import re
from functools import partial
from itertools import izip
from more_itertools import unique_everseen
from urlparse import urlparse

import arrow
import requests
from bs4 import BeautifulSoup
from funcy import notnone, walk_keys, without

from app import db
from utils import find_player_name, multiple_replace


_WINLOSS_REGEX = re.compile('.*?\((.*?)\)')


class Ingester(object):
    @staticmethod
    def _date_conversion(text):
        return arrow.get(text).datetime

    @staticmethod
    def _home_conversion(text):
        return text != '@'

    @staticmethod
    def _winloss_conversion(text):
        return float(_WINLOSS_REGEX.match(text).group(1))

    @staticmethod
    def _percent_conversion(text):
        return None

    @staticmethod
    def _plusminus_conversion(text):
        return float(text) if text else 0

    def find(self):
        """Adds all gamelogs from a basketball-reference url to the
        database."""
        page = requests.get(self._url, params=self._payload).text
        soup = BeautifulSoup(page)
        regular_table = soup.find('table', {'id': self._regular_id})
        playoff_table = soup.find('table', {'id': self._playoff_id})
        if regular_table:
            header_add = self._get_header_add(regular_table)
        else:
            header_add = self._get_header_add(playoff_table)
        if header_add:
            header = self._create_header(header_add)
            if regular_table:
                self._table_to_db('regular', regular_table, header)
            if playoff_table:
                self._table_to_db('playoff', playoff_table, header)

    @staticmethod
    def _get_header_add(table):
        """Finds and returns the header of a table."""
        def replace_titles(title):
            return multiple_replace(
                title,
                {'%': 'P', '3': 'T', '+/-': 'PlusMinus'})

        titles = (
            replace_titles(str(th.get_text()))
            for th in table.find_all('th')
        )
        return list(unique_everseen(titles))

    def _create_header(self, header_add):
        """Creates the initial header."""
        header = self._initial_header + header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')
        return without(header, 'FGP', 'FTP', 'TPP')

    def _table_to_db(self, season, table, header):
        """Adds all gamelogs in a table to the database."""
        gamelogs = []
        for row in table.find_all('tr'):
            stat_values_add = self._stat_values_parser(row.find_all('td'))
            # Skip headers.
            if not stat_values_add:
                continue
            stat_values = (
                self._initial_stat_values +
                [season] +
                stat_values_add
            )
            gamelogs.append(dict(izip(header, stat_values)))
        self._insert_gamelogs(gamelogs)

    @staticmethod
    def is_number(s):
        """Checks if a string is a number."""
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _stat_values_parser(self, cols):
        """Returns a list of values which change or skip the col strings based
        on their content."""
        def get_val(i, col):
            text = str(col.get_text())
            conversion = self._conversions.get(i)
            if conversion:
                return conversion(text)
            if self.is_number(text):
                return float(text)
            return text
        return filter(notnone, (get_val(i, col) for i, col in enumerate(cols)))


class GamelogIngester(Ingester):
    _initial_header = ['Player', 'PlayerCode', 'Year', 'Season']
    _payload = None
    _regular_id, _playoff_id = 'pgl_basic', 'pgl_basic_playoffs'

    def __init__(self, url):
        self._url = url
        path_components = urlparse(self._url).path.split('/')
        self._initial_stat_values = [
            find_player_name(path_components[3]),  # Player
            path_components[3],  # PlayerCode
            path_components[5]  # Year
        ]
        self._conversions = {
            2: self._date_conversion,
            5: self._home_conversion,
            7: self._winloss_conversion,
            12: self._percent_conversion,
            15: self._percent_conversion,
            18: self._percent_conversion
        }

    def _insert_gamelogs(self, gamelogs):
        """Adds gamelogs to the database."""
        db.gamelogs.insert(gamelogs)


class HeadtoheadIngester(Ingester):
    _initial_header = [
        'MainPlayer',
        'MainPlayerCode',
        'OppPlayer',
        'OppPlayerCode',
        'Season'
    ]
    _url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
    _regular_id, _playoff_id = 'stats_games', 'stats_games_playoffs'

    def __init_(self, player_combo):
        self.player_one_code, self.player_two_code = player_combo
        self._payload = {
            'p1': self.player_one_code,
            'p2': self.player_two_code,
            'request': 1
        }
        self._initial_stat_values = [
            find_player_name(self.player_one_code),  # MainPlayer
            self.player_one_code,  # MainPlayerCode
            find_player_name(self.player_two_code),  # OppPlayer
            self.player_two_code  # OppPlayerCode
        ]
        self._conversions = {
            2: self._date_conversion,
            5: self._home_conversion,
            7: self._winloss_conversion,
            12: self._percent_conversion,
            15: self._percent_conversion,
            18: self._percent_conversion,
            29: self._plusminus_conversion
        }

    def _insert_gamelogs(self, gamelogs):
        """Adds gamelogs to the database."""
        db.headtoheads.insert(
            self._update_gamelog_keys(gamelog) for gamelog in gamelogs)

    def _update_gamelog_keys(self, gamelog):
        """Removes Player key and switches MainPlayerCode and OppPlayerCode
        keys if the MainPlayerCode is not player_code."""
        # @TODO This is so sad.
        gamelog.pop('Player', None)
        if self.player_one_code != gamelog['MainPlayerCode']:
            replacer = partial(multiple_replace,
                               adict={'Main': 'Opp', 'Opp': 'Main'})
            return walk_keys(replacer, gamelog)
        return gamelog


class PlayerIngester(object):
    _br_url = 'http://www.basketball-reference.com'
    _date_regex = re.compile('\d{4}-\d{2}')

    def __init__(self, letter):
        self._letter = letter

    def find(self):
        """Finds the home urls for all players whose last names start with a
        particular letter."""
        # Current players are noted with bold text.
        url = "{self._br_url}/players/{self._letter}".format(self=self)
        letter_page = requests.get(url).text
        current_names = BeautifulSoup(letter_page).find_all('strong')
        if current_names:
            db.players.insert(
                self._create_player_dict(name) for name in current_names)

    def _get_gamelog_urls(self, player_url):
        """Returns list of gamelog urls with every year for one player."""
        player_page = requests.get(player_url).text
        tables = (BeautifulSoup(player_page)
                  .find('table', {'id': 'totals'})
                  .find_all('tr', {'class': 'full_table'}))
        return [
            self._br_url + link.get('href')
            for table in tables
            for link in table.find('td').find_all('a')
            if self._date_regex.match(str(link.get_text()))
        ]

    def _create_player_dict(self, name):
        """Create a dictionary for a player to enter into the database."""
        name_data = next(name.children)
        player_url = self._br_url + name_data.attrs['href']
        return {
            'Player': str(name_data.contents[0]),
            'GamelogURLs': self._get_gamelog_urls(player_url),
            'URL': player_url
        }
