import re
from itertools import islice, izip
from more_itertools import unique_everseen
from urlparse import urlparse

import arrow
import requests
from funcy import without
from pyquery import PyQuery as pq

from app import db
from utils import ConversionsMixin, is_number, find_player_name, multiple_replace


class Ingester(object):
    _winloss_regex = re.compile('.*?\((.*?)\)')

    def find(self):
        """Adds all gamelogs from a basketball-reference url to the database."""
        page = requests.get(self._url, params=self._payload).text
        d = pq(page)
        regular_table = d(self._regular_id)
        playoff_table = d(self._playoff_id)
        if not regular_table.length:
            regular_table = None
        if not playoff_table.length:
            playoff_table = None
        header_add = self._get_header_add(regular_table if regular_table else playoff_table)
        if header_add:
            header = self._create_header(header_add)
            if regular_table:
                self._table_to_db('regular', regular_table, header)
            if playoff_table:
                self._table_to_db('playoff', playoff_table, header)

    @staticmethod
    def _get_header_add(table):
        """Finds and returns the header of a table."""
        replacers = {'%': 'P', '3': 'T', '+/-': 'PlusMinus'}
        titles = (multiple_replace(str(th.text()), replacers) for th in table('th').items())
        return list(unique_everseen(titles))

    @classmethod
    def _create_header(cls, header_add):
        """Creates the initial header."""
        header = cls._initial_header + header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')
        return without(header, 'FGP', 'FTP', 'TPP')

    def _table_to_db(self, season, table, header):
        """Adds all gamelogs in a table to the database."""
        rows = table('tr').items()
        gamelogs = []
        for row in islice(rows, 1, None):
            cols = row('td').items()
            stat_values = (
                self._initial_stat_values + [season] + self._stat_values_parser(cols, season))
                gamelogs.append(dict(izip(header, stat_values)))
        self._gamelogs_insert(gamelogs)

    @classmethod
    def _stat_values_parser(cls, cols, season):
        """Returns a list of values which change or skip the col strings based on their content."""
        values = []
        for i, col in enumerate(cols):
            text = str(col.text())
            conversion = cls._conversions.get(i)
            if conversion:
                values.append(conversion(text))
            else:
                if is_number(text):
                    values.append(float(text))
                else:
                    values.append(text)
        return values


class GamelogIngester(Ingester):
    _initial_header = ['Player', 'PlayerCode', 'Year', 'Season']
    _conversions = {
        2: ConversionsMixin.date_conversion,
        4: ConversionsMixin.home_conversion,
        11: ConversionsMixin.percent_conversion,
        14: ConversionsMixin.percent_conversion,
        17: ConversionsMixin.percent_conversion,
    }
    _payload = None
    _regular_id, _playoff_id = '#pgl_basic', '#pgl_basic_playoffs'

    def __init__(self, url):
        self._url = url
        path_components = urlparse(self._url).path.split('/')
        # Player, PlayerCode, Year, Season
        self._initial_stat_values = [find_player_name(path_components[3]), path_components[3],
                                     path_components[5]]

    @staticmethod
    def _gamelogs_insert(gamelogs):
        """Adds gamelogs to the database."""
        db.gamelogs.insert(gamelogs)


class HeadtoheadIngester(Ingester):
    _initial_header = ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode', 'Season']
    _conversions = {
        2: ConversionsMixin.date_conversion,
        5: ConversionsMixin.home_conversion,
        7: ConversionsMixin.winloss_conversion,
        12: ConversionsMixin.percent_conversion,
        15: ConversionsMixin.percent_conversion,
        18: ConversionsMixin.percent_conversion,
        29: ConversionsMixin.plusminus_conversion
    }
    _url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
    _regular_id, _playoff_id = '#stats_games', '#stats_games_playoffs'

    def __init_(self, player_combo):
        self.player_one_code, self.player_two_code = player_combo
        self._payload = {'p1': self.player_one_code, 'p2': self.player_two_code, 'request': 1}
        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        self._initial_stat_values = [find_player_name(self.player_one_code), self.player_one_code,
                                     find_player_name(self.player_two_code), self.player_two_code]

    def _gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""
        db.headtoheads.insert(map(self._update_gamelog_keys, gamelogs))

    def _update_gamelog_keys(self, gamelog):
        """Removes Player key and switches MainPlayerCode and OppPlayerCode keys if the
        MainPlayerCode is not player_code."""
        # @TODO This is so sad.
        gamelog.pop('Player', None)
        if self.player_one_code != gamelog['MainPlayerCode']:
            changer = lambda title: title.replace('Main', 'Opp').replace('Opp', 'Main')
            return {changer(key): val for key, val in gamelog.iteritems()}
        return gamelog


class PlayerIngester(object):
    _br_url = 'http://www.basketball-reference.com'
    _date_regex = re.compile('\d{4}-\d{2}')

    def __init__(self, letter):
        self._letter = letter

    def find(self):
        """Finds the home urls for all players whose last names start with a particular letter."""
        # Current players are noted with bold text.
        letter_page = requests.get("{self._br_url}/players/{self._letter}".format(self=self)).text
        letter_d = pq(letter_page)
        current_names = letter_d('strong').items()
        db.players.insert(map(self._create_player_dict, current_names))

    @classmethod
    def _get_gamelog_urls(cls, player_url):
        """Returns list of gamelog urls with every year for one player."""
        player_page = requests.get(player_url).text
        tables = pq(player_page)('#totals')('.full_table').items()
        return [cls._br_url + link.attr('href')
                for table in tables
                for link in table('td')('a').items()
                if cls._date_regex.match(str(link.text()))]

    @classmethod
    def _create_player_dict(cls, name):
        """Create a dictionary for a player to enter into the database."""
        print name.text()
        player_url = cls._br_url + name('a').attr('href')
        return {
            'Player': str(name.text()),
            'GamelogURLs': cls._get_gamelog_urls(player_url),
            'URL': player_url
        }

