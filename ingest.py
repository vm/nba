import re
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import islice, izip
from urlparse import urlparse

import requests
from pyquery import PyQuery as pq

from app import db
from utils import is_number, find_player_name, find_player_code


class GamelogIngester(object):
    _winloss_regex = re.compile('.*?\((.*?)\)')

    _date_conversion = lambda text: datetime.strptime(text, '%Y-%m-%d')
    _home_conversion = lambda text != '@'
    _winloss_conversion = lambda text: float(_winloss_regex.match(text).group(1))
    _percent_conversion = None
    _plusminus_conversion = lambda text: float(text) if text else 0

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
            self._table_to_db('regular', regular_table, header)
            self._table_to_db('playoff', playoff_table, header)

    @staticmethod
    def _get_header_add(table):
        """Finds and returns the header of a table."""
        replacer = lambda t: t.replace('%', 'P').replace('3', 'T').replace('+/-', 'PlusMinus')
        titles = table('th').items()
        return (replacer(title.text()) for title in table('th').items()) else None

    @classmethod
    def _create_header(cls, header_add):
        """Creates the initial header."""
        header = cls._initial_header + header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')
        return filter(lambda title: title not in {'FGP', 'FTP', 'TPP'}, header)

    def _table_to_db(self, season, table, header):
        """Adds all gamelogs in a table to the database."""
        if not table:
            return
        rows = table('tr').items()
        gamelogs = []
        for row in islice(rows, 1, None):
            cols = row('td').items()
            if not cols.length:
                continue
            stat_values = (self._initialize_stat_values(season) +
                           self._stat_values_parser(cols))
            gamelogs.append(dict(izip(header, stat_values)))
        self._gamelogs_insert(gamelogs)

    @classmethod
    def _stat_values_parser(cls, cols, season):
        """Returns a list of values which change or skip the col strings based on their content."""
        for i, col in enumerate(cols):
            text = col.text()
            conversion = cls._conversions.get(i)
            parsed = conversion(text) if conversion else float(text) if is_number(text) else text
            if conversion:
                values.append(conversion(text))
            else:
                if is_number(text):
                    values.append(float(text))
                else:
                    values.append(text)
        return values


class BasicGamelogIngester(GamelogIngester):
    _initial_header = ['Player', 'PlayerCode', 'Year', 'Season']
    _conversions = {
        2: GamelogIngester._date_conversion,
        4: GamelogIngester._home_conversion,
        11: GamelogIngester._percentage_conversion,
        14: GamelogIngester._percentage_conversion,
        17: GamelogIngester._percentage_conversion,
    }
    _payload = None
    _regular_id, _playoff_id = '#pgl_basic', '#pgl_basic_playoffs'

    def __init__(self, url):
        self._url = url

    def initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""
        path_components = urlparse(self._url).path.split('/')
        # Player, PlayerCode, Year, Season.
        return [find_player_name(path_components[3]),
                path_components[3],
                path_components[5],
                season]

    @staticmethod
    def gamelogs_insert(gamelogs):
        """Adds gamelogs to the database."""
        db.gamelogs.insert(gamelogs)


class HeadtoheadGamelogIngester(GamelogIngester):
    _initial_header = ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode', 'Season']
    _conversions = {
        2: GamelogIngester._date_conversion,
        5: GamelogIngester._home_conversion
        7: GamelogIngester._winloss_conversion,
        12: GamelogIngester._percentage_conversion,
        15: GamelogIngester._percentage_conversion,
        18: GamelogIngester._percentage_conversion,
        29: GamelogIngester._plusminus_conversion
    }
    _url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
    _regular_id, _playoff_id = '#stats_games', '#stats_games_playoffs'

    def __init__(self, player_combo):
        self.player_one_code, self.player_two_code = player_combo
        self._payload = {'p1': self.player_one_code, 'p2': self.player_two_code, 'request': 1}

    def _initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""
        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        return [find_player_name(self.player_one_code),
                self.player_one_code,
                find_player_name(self.player_two_code),
                self.player_two_code,
                season]

    def _gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""
        db.headtoheads.insert(map(self._update_gamelog_keys, gamelogs))

    def _update_gamelog_keys(self, gamelog):
        """Removes Player key and switches MainPlayerCode and OppPlayerCode keys if the
        MainPlayerCode is not player_code."""
        gamelog.pop('Player', None)
        if self.player_one_code != gamelog['MainPlayerCode']:
            changer = lambda title: title.replace('Main', 'Opp').replace('Opp', 'Main')
            return {changer(key): val for key, val in gamelog.iteritems()}
        return gamelog


class PlayerIngester(object):
    _br_url = 'http://www.basketball-reference.com'
    _date_regex = re.compile('\d{4}-\d{2}')

    def __init__(self, letter):
        self.letter = letter

    def find(self):
        """Finds the home urls for all players whose last names start with a particular letter."""
        # Current players are noted with bold text.
        letter_page = requests.get("{self.br_url}/players/{self.letter}".format(self=self)).text
        letter_d = pq(letter_page)
        current_names = letter_d('strong').items()
        db.players.insert(map(create_player_dict, current_names))

    @classmethod
    def _get_gamelog_urls(cls, player_url):
        """ Returns list of gamelog urls with every year for one player."""
        player_page = requests.get(player_url).text
        player_d = pq(player_page)
        totals_table = player_d('#totals')
        all_tables = totals_table('.full_table').items()
        return [cls.br_url + link.attr('href')
                for table in all_tables
                for link in table('td')('a').items()
                if cls._date_regex.match(link.text())]

    @classmethod
    def _create_player_dict(cls, name):
        player_url = cls._br_url + name('a').attr('href')
        return {
            'Player': name.text(),
            'GamelogURLs': cls._get_gamelog_urls(player_url),
            'URL': player_url
        }

