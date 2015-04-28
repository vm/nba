import re
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import combinations, islice
from multiprocessing import Pool
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq

from .app import db
from .utils import is_number, find_player_name, find_player_code

# Regexes to find data in table cell text.
PLUSMINUS_REGEX = re.compile('.*?\((.*?)\)')
DATE_REGEX = re.compile('\d{4}-\d{2}')

class GamelogIngester(object):
    """
    Adds all the gamelogs on a particular page to the database.
    """

    def __init__(self, collection, url=None, player_combo=None):
        """
        :param collection: Name of a collection in the nba database.
        :param url: (optional) Basketball-Reference url for a single year of
            gamelogs for a player to add to gamelogs collection.
        :param player_combo: (optional) Basketball-Reference codes for two
            players used to add to headtoheads collection.
        """

        # General
        self.collection = collection

        # Based on collection
        if self.collection == 'gamelogs':
            self.url = url
            self.offset = 1
            # Name of the regular season table on the page.
            self.regular_id = '#pgl_basic'
            # Name of the playoff table on the page.
            self.playoff_id = '#pgl_basic_playoffs'
            self.page = requests.get(self.url).text
        if self.collection == 'headtoheads':
            # Base url for head2headfinder on basketball reference.
            self.url = ('http://www.basketball-reference.com/play-index/'
                        'h2h_finder.cgi')
            self.offset = 0
            self.player_code, self.player_code_2 = player_combo
            # Params for the payload on a url request.
            self.payload = {'p1': self.player_code,
                            'p2': self.player_code_2,
                            'request': 1}
            # Name of the regular season table on the page.
            self.regular_id = '#stats_games'
            # Name of the playoff table on the page.
            self.playoff_id = '#stats_games_playoffs'
            self.page = requests.get(self.url, params=self.payload).text

        # Scraping
        self.d = pq(self.page)
        self.regular_table = self.d(self.regular_id)
        self.playoff_table = self.d(self.playoff_id)

        # Check if tables exist.
        if self.regular_table.length == 0:
            self.regular_table = None
        if self.playoff_table.length == 0:
            self.playoff_table = None

        # Header
        # Gets the initial header from the basketball reference table.
        self.header_add = self.get_header(
            self.regular_table if self.regular_table else self.playoff_table)
        if self.header_add:
            # Creates the complete header by adding missing and fixing titles.
            self.header = self.create_header()

    def find_gamelogs(self):
        """
        Adds all gamelogs from a basketball-reference url to the database.
        """

        # If no header, that means no matchups between a player combo exist.
        if self.header_add:
            self.table_to_db('regular', self.regular_table)
            self.table_to_db('playoff', self.playoff_table)

    @staticmethod
    def get_header(table):
        """
        Finds and returns the header of a table.

        :param table:
        :returns: Header from table, None if AttributeError.
        """

        def replacer(title):
            """
            Creates a title by replacing parts of the given string to remove
            any numbers or symbols.

            :param title: Initial title string.
            :returns: Replaced title.
            """

            for switch in {('%', 'P'), ('3', 'T'), ('+/-', 'PlusMinus')}:
                initial, final = switch
                title = title.replace(initial, final)
            return title

        try:
            header = (replacer(str(th.text()))  # Gets header text.
                      for th in table('th').items())  # Finds header titles.
            return list(OrderedDict.fromkeys(header))  # Removes duplicates.
        except AttributeError:
            return None

    def create_header(self):
        """
        Creates the initial header.

        :returns: Header list.
        """

        header = self.initialize_header() + self.header_add
        header[9] = 'Home'  # Replaces empty column.
        header.insert(11, 'WinLoss')  # Inserts missing column.

        # Remove all percentages
        return [title
                for title in header
                if title not in {'FGP', 'FTP', 'TPP'}]

    def table_to_db(self, season, table):
        """
        Adds all gamelogs in a table to the database.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :param table: Table of gamelog stats for one year.
        """

        if not table:
            return

        rows = table('tr').items()

        # Each row is one gamelog.
        gamelogs = []

        # All rows except header.
        for row in islice(rows, 1, None):
            cols = row('td').items()

            if cols.length == 0:
                continue

            # Each column is one stat type.
            stat_values = self.stat_values_parser(cols, season)

            # Zips the each header item and stat value together and adds each
            # into a dictionary, creating a dict of gamelog stats for a game.
            gamelog = dict(zip(self.header, stat_values))
            gamelogs.append(gamelog)

        # Inserts the found gamelogs into the database at once.
        self.gamelogs_insert(gamelogs)

    def stat_values_parser(self, cols, season):
        """
        Loops through of a list of columns and returns a list of values which
        change or skip the col strings based on their content.

        :param cols: List of column values in a single gamelog.
        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Parsed stat values.
        """

        def convert(i, col):
            text = str(col.text())
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
            # Skip them because they can be calculated manually.
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
                [col
                 for col in (convert(i, col) for i, col in enumerate(cols))
                 if col is not None])


class BasicGamelogIngester(GamelogIngester):
    """
    Adds all single-player gamelogs for single page to the database.
    """

    def __init__(self, url):
        """
        :param url: Basketball-Reference url for a single year of gamelogs for
            a player to add to gamelogs collection.
        """

        super().__init__('gamelogs', url=url)

    def initialize_header(self):
        """
        Initializes the header with manually added values and calls header_add.

        :returns: Initialized header.
        """

        return ['Player', 'PlayerCode', 'Year', 'Season']

    def initialize_stat_values(self, season):
        """
        Initializes the stat values with manually added values.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Initialized stat values.
        """

        path_components = urlparse(self.url).path.split('/')
        # Player, PlayerCode, Year, Season.
        return [find_player_name(path_components[3]),
                path_components[3],
                path_components[5],
                season]

    def gamelogs_insert(self, gamelogs):
        """
        Adds gamelogs to the database.

        :param gamelogs:
        """

        db.gamelogs.insert(gamelogs)
        print(self.url)


class HeadtoheadGamelogIngester(GamelogIngester):
    """
    Adds all headtohead gamelogs for a single page to the database.
    """

    def __init__(self, player_combo):
        """
        :param player_combo: Basketball-Reference codes for two players used to
            add to headtoheads collection.
        """

        super().__init__('headtoheads', player_combo=player_combo)

    def initialize_header(self):
        """
        Initializes the header with manually added values and calls header_add.

        :returns: Initialized header.
        """

        return ['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode',
                'Season']

    def initialize_stat_values(self, season):
        """
        Initializes the stat values with manually added values.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Initialized stat values.
        """

        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        return [find_player_name(self.player_code),
                self.player_code,
                find_player_name(self.player_code_2),
                self.player_code_2,
                season]

    def gamelogs_insert(gamelogs):
        """
        Adds gamelogs to the database.

        :param gamelogs:
        """

        gamelogs = [self.update_gamelog_keys(gamelog) for gamelog in gamelogs]
        db.headtoheads.insert(gamelogs)
        print(self.player_code, self.player_code_2)

    def update_gamelog_keys(self, gamelog):
        """
        Removes Player key and switches MainPlayerCode and OppPlayerCode keys
        if the MainPlayerCode is not player_code.

        :param gamelog:
        :returns: Updated gamelog.
        """

        gamelog.pop('Player', None)

        if self.player_code != gamelog['MainPlayerCode']:
            def changer(title):
                """
                Switches items containing Main with Opp in the header and vice
                versa.

                :param title: Name to potentially replace.
                :returns: Replaced title.
                """

                s = ('Main', 'Opp')
                return title.replace(*s if 'Main' in title else *s[::-1])

            gamelog = {changer(key): val for key, val in gamelog.items()}

        return gamelog


class PlayerIngester(object):
    """
    Adds all players from a letter to the database.
    """

    def __init__(self, letter):
        """
        :param letter: The letter for which players should be found.
        """

        self.letter = letter
        self.br_url = 'http://www.basketball-reference.com'
        self.letter_page = requests.get(
            "{self.br_url}/players/{self.letter}".format(self=self)).text
        self.letter_d = pq(self.letter_page)

    def get_gamelog_urls(self, player_url):
        """
        Returns list of gamelog urls with every year for one player.

        :param player_url:
        :returns: All the links to seasons for a player.
        """

        player_page = requests.get(player_url).text
        player_d = pq(player_page)

        # Table containing player totals.
        totals_table = player_d('#totals')
        # All single season tables.
        all_tables = totals_table('.full_table').items()

        # Finds all links in all the season tables.
        return [self.br_url + link.attr('href')
                for table in all_tables
                for link in table('td')('a').items()
                if DATE_REGEX.match(link.text())]

    def create_player_dict(self, name):
        """
        :param name:
        """

        player_url = self.br_url + name('a').attr('href')
        return {'Player': str(name.text()),
                'GamelogURLs': self.get_gamelog_urls(player_url),
                'URL': player_url}

    def find_players(self):
        """
        Finds the home urls for all players whose last names start with a
        particular letter.
        """

        # Current players are noted with bold text.
        current_names = self.letter_d('strong').items()

        # Adds a dict with keys Player, GamelogURLs and URL to players for
        # each current_player.
        players = [self.create_player_dict(name)
                   for name in current_names]

        # Only inserts if there are any players for the letter.
        if players:
            db.players.insert(players)
            print(self.letter)


# Multiprocessing forces these functions to be top level and non-lambdas.
def gamelogs_from_url(url):
    BasicGamelogIngester(url).find_gamelogs()


def headtoheads_from_combo(combo):
    HeadtoheadGamelogIngester(combo).find_gamelogs()


def players_from_letter(letter):
    PlayerIngester(letter).find_players()


class CollectionCreator(object):
    """
    Creates a complete collection of either players or gamelogs.
    """
    def __init__(self, collection, update=True):
        """
        :param collection: Name of a collection in the nba database.
        :param update: (optional) Whether to only update gamelogs collection.
        """

        self.collection = collection
        self.update = update
        self.p = Pool(20)
        self.options = self.find_options()

    def find_options(self):
        """
        Finds a options to add to the database based on the collection.

        :returns: A list of potential options.
        """

        if self.collection == 'players':
            return 'abcdefghijklmnopqrstuvwxyz'

        players = db.players.find()
        if self.collection == 'gamelogs':
            self_update = self.update
            return (url
                    for player in players
                    for url in player['GamelogURLs']
                    if not self_update or '2015' in url)
        if self.collection == 'headtoheads':
            player_names = (find_player_code(player['Player'])
                            for player in players)
            return combinations(player_names, 2)

    def mapper(self, f):
        """
        Calls Pool map on the given function for self.options.

        :param f: The function to map.
        """

        self.p.map(f, self.options)

    def create(self):
        """
        Creates a complete collection in the database.
        """

        if self.collection == 'gamelogs':
            # Deletes all gamelogs from current season if update.
            if self.update:
                db.gamelogs.remove({'Year': 2015})
            f = gamelogs_from_url
        if self.collection == 'headtoheads':
            f = headtoheads_from_combo
        if self.collection == 'players':
            f = players_from_letter
        self.mapper(f)

