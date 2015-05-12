from __future__ import print_function, absolute_import

import re
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import combinations, islice, izip
from multiprocessing import Pool
if sys.version_info > (3, 0):
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

import requests
from pyquery import PyQuery as pq

from .app import db
from .utils import is_number, find_player_name, find_player_code

PLUSMINUS_REGEX = re.compile('.*?\((.*?)\)')
DATE_REGEX = re.compile('\d{4}-\d{2}')

class GamelogIngester(object):
    """Adds all the gamelogs on a particular page to the database."""

    def __init__(self, collection, url=None, player_combo=None):
        self.collection = collection
        if self.collection == 'gamelogs':
            self.url = url
            self.offset = 1
            self.regular_id, self.playoff_id = '#pgl_basic', '#pgl_basic_playoffs'
            self.page = requests.get(self.url).text
        else:
            self.url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
            self.offset = 0
            self.player_one_code, self.player_two_code = player_combo
            self.payload = {'p1': self.player_one_code, 'p2': self.player_two_code, 'request': 1}
            self.regular_id, self.playoff_id = '#stats_games', '#stats_games_playoffs'
            self.page = requests.get(self.url, params=self.payload).text

        self.d = pq(self.page)
        self.regular_table = self.d(self.regular_id)
        self.playoff_table = self.d(self.playoff_id)

        if self.regular_table.length == 0:
            self.regular_table = None
        if self.playoff_table.length == 0:
            self.playoff_table = None

        self.header_add = self.get_header(
            self.regular_table if self.regular_table else self.playoff_table)
        if self.header_add:
            self.header = self.create_header()

    def find(self):
        """Adds all gamelogs from a basketball-reference url to the database."""

        if self.header_add:
            self.table_to_db('regular', self.regular_table)
            self.table_to_db('playoff', self.playoff_table)

    @staticmethod
    def get_header(table):
        """Finds and returns the header of a table."""

        def replacer(title):
            """Creates a title by replacing parts of the given string to remove any numbers or
            symbols."""

            for (initial_str, final_str) in {('%', 'P'), ('3', 'T'), ('+/-', 'PlusMinus')}:
                title = title.replace(initial_str, final_str)
            return title

        header = (replacer(th.text()) for th in table('th').items())
        return list(OrderedDict.fromkeys(header)) if header else None

    def create_header(self):
        """Creates the initial header."""

        header = self.initialize_header() + self.header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')

        return [title for title in header if title not in {'FGP', 'FTP', 'TPP'}]

    def table_to_db(self, season, table):
        """Adds all gamelogs in a table to the database."""

        if not table:
            return
        rows = table('tr').items()
        gamelogs = []
        for row in islice(rows, 1, None):
            cols = row('td').items()
            if cols.length == 0:
                continue
            stat_values = self.stat_values_parser(cols, season)
            gamelogs.append(dict(izip(self.header, stat_values)))
        self.gamelogs_insert(gamelogs)

    def stat_values_parser(self, cols, season):
        """Returns a list of values which change or skip the col strings based on their content."""

        def convert(i, col):
            text = col.text()
            # Date
            if i == 2:
                return datetime.strptime(text, '%Y-%m-%d')
            # Home
            if i == 4 + self.offset:
                return text != '@'
            # WinLoss
            if i == 7 and self.offset:
                return float(PLUSMINUS_REGEX.match(text).group(1))
            # Percentages
            if i in (n + self.offset for n in {11, 14, 17}):
                return None
            # PlusMinus
            if i == 29 and self.offset:
                return 0 if text == '' else float(text)
            # Number
            if is_number(text):
                return float(text)
            # Text
            return text

        return (self.initialize_stat_values(season) +
                [col for col in (convert(i, col) for i, col in enumerate(cols))
                 if col is not None])


class BasicGamelogIngester(GamelogIngester):
    """Adds all single-player gamelogs for single page to the database."""

    def __init__(self, url):
        super(BasicGamelogIngester, self).__init__('gamelogs', url=url)

    def initialize_header(self):
        """Initializes the header with manually added values and calls header_add."""

        return ['Player', 'PlayerCode', 'Year', 'Season']

    def initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""

        path_components = urlparse(self.url).path.split('/')
        # Player, PlayerCode, Year, Season.
        return [find_player_name(path_components[3]), path_components[3], path_components[5],
                season]

    def gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""

        db.gamelogs.insert(gamelogs)
        print(self.url)


class HeadtoheadGamelogIngester(GamelogIngester):
    """Adds all headtohead gamelogs for a single page to the database."""

    def __init__(self, player_combo):
        super(HeadtoheadGamelogIngester, self).__init__('headtoheads', player_combo=player_combo)

    def initialize_header(self):
        """Initializes the header with manually added values and calls header_add."""

        return ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode', 'Season']

    def initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""

        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        return [find_player_name(self.player_one_code), self.player_one_code,
                find_player_name(self.player_two_code), self.player_two_code, season]

    def gamelogs_insert(gamelogs):
        """Adds gamelogs to the database."""

        db.headtoheads.insert(map(self.update_gamelog_keys, gamelogs))
        print(self.player_one_code, self.player_two_code)

    def update_gamelog_keys(self, gamelog):
        """Removes Player key and switches MainPlayerCode and OppPlayerCode keys if the
        MainPlayerCode is not player_code."""

        gamelog.pop('Player', None)
        if self.player_one_code != gamelog['MainPlayerCode']:
            def changer(title):
                """Switches items containing Main with Opp in the header and vice versa."""

                s = ('Main', 'Opp') if 'Main' in title else ('Opp', 'Main')
                return title.replace(*s)

            gamelog = {changer(key): val for key, val in gamelog.items()}
        return gamelog


class PlayerIngester(object):
    """Adds all players from a letter to the database."""

    def __init__(self, letter):
        self.letter = letter
        self.br_url = 'http://www.basketball-reference.com'
        self.letter_page = requests.get(
            "{self.br_url}/players/{self.letter}".format(self=self)).text
        self.letter_d = pq(self.letter_page)
        print(self.letter_d)

    def get_gamelog_urls(self, player_url):
        """ Returns list of gamelog urls with every year for one player."""

        player_page = requests.get(player_url).text
        player_d = pq(player_page)

        totals_table = player_d('#totals')
        all_tables = totals_table('.full_table').items()
        print(totals_table)

        return [self.br_url + link.attr('href')
                for table in all_tables
                for link in table('td')('a').items()
                if DATE_REGEX.match(link.text())]

    def create_player_dict(self, name):
        player_url = self.br_url + name('a').attr('href')
        return {'Player': name.text(),
                'GamelogURLs': self.get_gamelog_urls(player_url),
                'URL': player_url}

    def find(self):
        """Finds the home urls for all players whose last names start with a particular letter."""

        # Current players are noted with bold text.
        current_names = self.letter_d('strong').items()
        db.players.insert(map(create_player_dict, current_names))
        print(self.letter)


# Multiprocessing forces these functions to be top level.
def gamelogs_from_url(url):
    BasicGamelogIngester(url).find()


def headtoheads_from_combo(combo):
    HeadtoheadGamelogIngester(combo).find()


def players_from_letter(letter):
    PlayerIngester(letter).find()


class CollectionCreator(object):
    """Creates a complete collection of either players or gamelogs."""
    def __init__(self, collection, update=True):
        self.collection = collection
        self.update = update
        self.p = Pool(20)
        self.options = self.find_options()

    def find_options(self):
        """Finds a options to add to the database based on the collection."""

        if self.collection == 'players':
            return 'abcdefghijklmnopqrstuvwxyz'
        players = db.players.find()
        if self.collection == 'gamelogs':
            self_update = self.update
            return (url for player in players for url in player['GamelogURLs']
                    if not self_update or '2015' in url)
        else:
            return combinations((find_player_code(player['Player']) for player in players), 2)

    def mapper(self, f):
        """Calls Pool map on the given function for self.options."""

        self.p.map(f, self.options)

    def create(self):
        """Creates a complete collection in the database."""

        if self.collection == 'gamelogs':
            if self.update:
                db.gamelogs.remove({'Year': 2015})
            f = gamelogs_from_url
        elif self.collection == 'headtoheads':
            f = headtoheads_from_combo
        else:
            f = players_from_letter
        self.mapper(f)
