import re
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import combinations, islice, izip
from urlparse import urlparse

import requests
from pyquery import PyQuery as pq

from nba.app import db
from nba.utils import is_number, find_player_name, find_player_code

PLUSMINUS_REGEX = re.compile('.*?\((.*?)\)')
DATE_REGEX = re.compile('\d{4}-\d{2}')


class GamelogIngester(object):
    date = lambda text: datetime.strptime(text, '%Y-%m-%d')
    home = lambda text != '@'
    winloss = lambda text: float(PLUSMINUS_REGEX.match(text).group(1))
    percent = lambda text: None
    plusminus = lambda text: float(text) if text else 0
    number = lambda text: float(text)
    text = lambda text: text

    def find(self):
        """Adds all gamelogs from a basketball-reference url to the database."""
        page = requests.get(self.url, params=self.payload).text
        d = pq(page)
        regular_table = d(self.regular_id)
        playoff_table = d(self.playoff_id)

        if not regular_table.length:
            regular_table = None
        if not playoff_table.length:
            playoff_table = None

        header_add = self.get_header(regular_table if regular_table else playoff_table)
        if header_add:
            header = self.create_header(header_add)
            self.table_to_db('regular', self.regular_table, header)
            self.table_to_db('playoff', self.playoff_table, header)

    @staticmethod
    def get_header(table):
        """Finds and returns the header of a table."""
        def replacer(title):
            """Creates a title by replacing parts of the given string to remove any numbers or
            symbols."""
            replacers = {('%', 'P'), ('3', 'T'), ('+/-', 'PlusMinus')}
            return reduce(lambda title, replacer: title.replace(*replacer), replacers, title)

        header = (replacer(th.text()) for th in table('th').items())
        return list(OrderedDict.fromkeys(header)) if header else None

    def create_header(self, header_add):
        """Creates the initial header."""
        header = self.initial_header + header_add
        header[9] = 'Home'
        header.insert(11, 'WinLoss')
        return filter(lambda title: title not in {'FGP', 'FTP', 'TPP'}, header)

    def table_to_db(self, season, table):
        """Adds all gamelogs in a table to the database."""
        if not table:
            return
        rows = table('tr').items()
        gamelogs = []
        for row in islice(rows, 1, None):
            cols = row('td').items()
            if not cols.length:
                continue
            stat_values = (self.initialize_stat_values(season) +
                           self.stat_values_parser(cols))
            gamelogs.append(dict(izip(self.header, stat_values)))
        self.gamelogs_insert(gamelogs)

    @classmethod
    def stat_values_parser(cls, cols, season):
        """Returns a list of values which change or skip the col strings based on their content."""
        parsed_values = []
        for i, col in enumerate(cols):
            text = col.text()
            conversion = cls.conversions.get(i)
            if conversion:
                parsed_values.append(conversion(text))
            else:
                parsed_values.append(cls.number(text) if is_number(text) else text)
        return parsed_values


class BasicGamelogIngester(GamelogIngester):
    initial_header = ['Player', 'PlayerCode', 'Year', 'Season']
    conversions = {
        2: GamelogIngester.date,
        4: GamelogIngester.home,
        11: GamelogIngester.percentage,
        14: GamelogIngester.percentage,
        17: GamelogIngester.percentage,
    }

    def __init__(self, url):
        self.collection = 'gamelogs'
        self.url = url
        self.payload = None
        self.regular_id, self.playoff_id = '#pgl_basic', '#pgl_basic_playoffs'

    def initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""
        path_components = urlparse(self.url).path.split('/')
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
    initial_header = ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode', 'Season']
    conversions = {
        2: GamelogIngester.date,
        5: GamelogIngester.home,
        7: GamelogIngester.winloss,
        12: GamelogIngester.percentage,
        15: GamelogIngester.percentage,
        18: GamelogIngester.percentage,
        29: GamelogIngester.plusminus
    }

    def __init__(self, player_combo):
        self.collection = 'headtoheads'
        self.url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'
        self.player_one_code, self.player_two_code = player_combo
        self.payload = {'p1': self.player_one_code, 'p2': self.player_two_code, 'request': 1}
        self.regular_id, self.playoff_id = '#stats_games', '#stats_games_playoffs'

    def initialize_stat_values(self, season):
        """Initializes the stat values with manually added values."""
        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        return [find_player_name(self.player_one_code),
                self.player_one_code,
                find_player_name(self.player_two_code),
                self.player_two_code,
                season]

    def gamelogs_insert(self, gamelogs):
        """Adds gamelogs to the database."""
        db.headtoheads.insert(map(self.update_gamelog_keys, gamelogs))

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

        return [self.br_url + link.attr('href')
                for table in all_tables
                for link in table('td')('a').items()
                if DATE_REGEX.match(link.text())]

    def create_player_dict(self, name):
        player_url = self.br_url + name('a').attr('href')
        return {
            'Player': name.text(),
            'GamelogURLs': self.get_gamelog_urls(player_url),
            'URL': player_url
        }

    def find(self):
        """Finds the home urls for all players whose last names start with a particular letter."""
        # Current players are noted with bold text.
        current_names = self.letter_d('strong').items()
        db.players.insert(map(create_player_dict, current_names))

