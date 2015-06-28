import re
from functools import partial
from more_itertools import unique_everseen
from urlparse import urlparse

import requests
from bs4 import BeautifulSoup
from funcy import notnone, walk_keys, without, zipdict

from app import db
from utils import ConversionsMixin, is_number, find_player_name, multiple_replace


class Ingester(ConversionsMixin):
    def find(self):
        """Adds all gamelogs from a basketball-reference url to the database."""
        page = requests.get(self._url, params=self._payload).text
        soup = BeautifulSoup(page)
        regular_table = soup.find('table', {'id': self._regular_id})
        playoff_table = soup.find('table', {'id': self._playoff_id})
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
        titles = (multiple_replace(str(th.getText()), {'%': 'P', '3': 'T', '+/-': 'PlusMinus'})
                  for th in table.findAll('th'))
        return list(unique_everseen(titles))

    def _create_header(self, header_add):
        """Creates the initial header."""
        header = self._initial_header + header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')
        return without(header, 'FGP', 'FTP', 'TPP')

    def _table_to_db(self, season, table, header):
        """Adds all gamelogs in a table to the database."""
        def create_gamelog(row):
            stat_values = (self._initial_stat_values + [season] +
                           self._stat_values_parser(row.findAll('td'), season))
            return zipdict(header, stat_values)
        # Skip header.
        self._gamelogs_insert((create_gamelog(row) for row in table.findAll('tr')[1:]))

    def _stat_values_parser(self, cols, season):
        """Returns a list of values which change or skip the col strings based on their content."""
        def get_val(i, col):
            text = str(col.getText())
            conversion = self._conversions.get(i)
            if conversion:
                return conversion(text)
            if is_number(text):
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
        # Player, PlayerCode, Year, Season
        self._initial_stat_values = [find_player_name(path_components[3]), path_components[3],
                                     path_components[5]]
        self._conversions = {2: self._date_conversion, 5: self._home_conversion,
                             7: self._winloss_conversion, 12: self._percent_conversion,
                             15: self._percent_conversion, 18: self._percent_conversion}

    def _gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""
        db.gamelogs.insert(gamelogs)


class HeadtoheadIngester(Ingester):
    _initial_header = ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode', 'Season']
    _url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
    _regular_id, _playoff_id = 'stats_games', 'stats_games_playoffs'

    def __init_(self, player_combo):
        self.player_one_code, self.player_two_code = player_combo
        self._payload = {'p1': self.player_one_code, 'p2': self.player_two_code, 'request': 1}
        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        self._initial_stat_values = [find_player_name(self.player_one_code), self.player_one_code,
                                     find_player_name(self.player_two_code), self.player_two_code]
        # TODO: these might be wrong conversions...
        self._conversions = {2: self._date_conversion, 5: self._home_conversion,
                             7: self._winloss_conversion, 12: self._percent_conversion,
                             15: self._percent_conversion, 18: self._percent_conversion,
                             29: self._plusminus_conversion}

    def _gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""
        db.headtoheads.insert(map(self._update_gamelog_keys, gamelogs))

    def _update_gamelog_keys(self, gamelog):
        """Removes Player key and switches MainPlayerCode and OppPlayerCode keys if the
        MainPlayerCode is not player_code."""
        # @TODO This is so sad.
        gamelog.pop('Player', None)
        if self.player_one_code != gamelog['MainPlayerCode']:
            return walk_keys(partial(multiple_replace, adict={'Main': 'Opp', 'Opp': 'Main'}),
                             gamelog)
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
        current_names = BeautifulSoup(letter_page).findAll('strong')
        players = map(self._create_player_dict, current_names)
        if players:
            db.players.insert(players)

    def _get_gamelog_urls(self, player_url):
        """Returns list of gamelog urls with every year for one player."""
        player_page = requests.get(player_url).text
        tables = (BeautifulSoup(player_page)
                .find('table', {'id': 'totals'})
                .findAll('tr', {'class': 'full_table'}))
        return [self._br_url + link.get('href')
                for table in tables
                for link in table.find('td').findAll('a')
                if self._date_regex.match(str(link.getText()))]

    def _create_player_dict(self, name):
        """Create a dictionary for a player to enter into the database."""
        name_data = next(name.children)
        player_url = self._br_url + name_data.attrs['href']
        return {'Player': str(name_data.contents[0]),
                'GamelogURLs': self._get_gamelog_urls(player_url),
                'URL': player_url}
