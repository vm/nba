import os
import re
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import combinations, izip
from urlparse import urlparse

import dill
import requests
from bs4 import BeautifulSoup, SoupStrainer
from pathos.multiprocessing import Pool

from app import db
from utils import is_number, find_player_name


class Ingester(object):
    """
    Adds all the gamelogs on a particular page to the database.
    """
    def __init__(self, collection, url=None, player_combo=None):
        """
        :param collection: Name of a collection in the nba database.
        :param url: (optional) Basketball-Reference url for a single year of
            gamelogs for a player to add to gamelogs collection.
        :param player_combo: (optional) Basketball-Reference codes for two
            players used to add to hths collection.
        """
        # General
        self.collection = collection

        # Based on collection
        if self.collection == 'gamelogs':
            self.url = url
            # Name of the regular season table on the page.
            self.regular_table_id = 'pgl_basic'
            # Name of the playoff table on the page.
            self.playoff_table_id = 'pgl_basic_playoffs'
            self.page = requests.get(self.url).text
        else:
            # Base url for head2headfinder on basketball reference.
            self.url = ('http://www.basketball-reference.com/play-index/'
                        'h2h_finder.cgi')
            self.player_code, self.player_code_2 = player_combo
            # Params for the payload on a url request.
            self.payload = {
                'p1': self.player_code,
                'p2': self.player_code_2,
                'request': 1
            }
            # Name of the regular season table on the page.
            self.regular_table_id='stats_games'
            # Name of the playoff table on the page.
            self.playoff_table_id='stats_games_playoffs'
            self.page = requests.get(self.url, params=self.payload).text

        # Scraping
        page_content = SoupStrainer('div', {'id': 'page_content'})
        self.soup = BeautifulSoup(self.page, parse_only=page_content)
        self.regular_table = self.soup.find('table',
                                            {'id': self.regular_table_id})
        self.playoff_table = self.soup.find('table',
                                            {'id': self.playoff_table_id})

        # Header
        # Gets the initial header from the basketball reference table.
        self.header_add = self.get_header(self.regular_table)
        if self.header_add:
            # Creates the complete header by adding missing and fixing titles.
            self.header = self.create_header()

    def get_header(self, table):
        """
        Finds and returns the header of a table.

        :returns: Header from table.
        :returns: None if AttributeError.
        """
        def col_title(th):
            """
            Replaces the titles in header so there are no numbers or symbols.

            :param th:
            """
            return th.replace('%','P') \
                     .replace('3','T') \
                     .replace('+/-','PlusMinus')

        try:
            header = [
                col_title(str(th.getText()))  # Gets header text.
                for th in table.findAll('th')  # Finds all header titles.
            ]
            return list(OrderedDict.fromkeys(header))  # Removes duplicates.
        except AttributeError:
            return None

    def find_gamelogs(self):
        """
        Adds all gamelogs from a basketball-reference url to the database.
        """
        # If no header, that means no matchups between a player combo exist.
        if not self.header_add:
            return

        self.table_to_db('regular', self.regular_table)
        self.table_to_db('playoff', self.playoff_table)

    def create_header(self):
        """
        Creates the initial header.
        :returns: Header list.
        """
        header = self.initialize_header()
        header[9] = 'Home'  # Replaces empty column.
        header.insert(11, 'WinLoss')  # Inserts missing column.

        # Remove all percentages
        return filter(lambda title: title not in {'FGP', 'FTP', 'TPP'}, header)

    def table_to_db(self, season, table):
        """
        Adds all gamelogs in a table to the database.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :param table: Table of gamelog stats for one year.
        """
        if not table:
            return

        rows = table.findAll('tr')
        del rows[0]  # Delete header row.

        # Each row is one gamelog.
        gamelogs = []
        for row in rows:
            cols = row.findAll('td')
            # Skip this iteration is there are no cols.
            if not cols:
                continue

            # Each column is one stat type.
            stat_values = self.stat_values_parser(cols, season)

            # Zips the each header item and stat value together and adds each
            # into a dictionary, creating a dict of gamelog stats for a game.
            gamelog = dict(izip(self.header, stat_values))
            gamelogs.append(gamelog)

        # Inserts the found gamelogs into the database at once.
        self.gamelogs_insert(gamelogs)


class GamelogIngester(Ingester):
    def __init__(self, url):
        """
        :param url: Basketball-Reference url for a single year of gamelogs for
            a player to add to gamelogs collection.
        """
        super(GamelogIngester, self).__init__('gamelogs', url=url)

    def initialize_header(self):
        """
        Initializes the header with manually added values and calls header_add.

        :returns: Initialized header.
        """
        return (['Player', 'PlayerCode', 'Year', 'Season'] + self.header_add)

    def initialize_stat_values(self, season):
        """
        Initializes the stat values with manually added values.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Initialized stat values.
        """

        path_components = urlparse(self.url).path.split('/')
        # Player, PlayerCode, Year, Season.
        return [
            find_player_name(path_components[3]),
            path_components[3],
            path_components[5],
            season
        ]

    def gamelogs_insert(self, gamelogs):
        """
        Adds gamelogs to the database.

        :param gamelogs:
        """
        db.gamelogs.insert(gamelogs)
        print self.url

    def stat_values_parser(self, cols, season):
        """
        Loops through of a list of columns and returns a list of values which
        change or skip the col strings based on their content.

        :param stat_values: Initial values list.
        :param cols: List of column values in a single gamelog.
        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Parsed stat values.
        """
        stat_values = self.initialize_stat_values(season)
        for i, col in enumerate(cols):
            text = str(col.getText())
            # Date
            if i == 2:
                stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
            # Home
            elif i == 5:
                stat_values.append(False if text == '@' else True)
            # WinLoss
            elif i == 7:
                plusminus = re.compile('.*?\((.*?)\)')
                stat_values.append(float(plusminus.match(text).group(1)))
            # Percentages
            # Skip them because they can be calculated manually.
            elif i in {12, 15, 18}:
                pass
            # PlusMinus
            elif i == 29:
                stat_values.append(0 if text == '' else float(text))
            # Number
            elif is_number(text):
                stat_values.append(float(text))
            # Text
            else:
                stat_values.append(text)
        return stat_values


class HthIngester(Ingester):
    def __init__(self, player_combo):
        """
        :param player_combo: Basketball-Reference codes for two players used to
            add to hths collection.
        """
        super(HthIngester, self).__init__('hths', player_combo=player_combo)

    def initialize_header(self):
        """
        Initializes the header with manually added values and calls header_add.

        :returns: Initialized header.
        """
        return (['MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode',
                 'Season'] + self.header_add)

    def initialize_stat_values(self, season):
        """
        Initializes the stat values with manually added values.

        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Initialized stat values.
        """
        # MainPlayerCode, MainPlayer, OppPlayerCode, OppPlayerCode, Season
        return [
            find_player_name(self.player_code),
            self.player_code,
            find_player_name(self.player_code_2),
            self.player_code_2,
            season
        ]

    def gamelogs_insert(self, gamelogs):
        """
        Adds gamelogs to the database.

        :param gamelogs:
        """
        gamelogs = [self.update_hth_gamelog_keys(g) for g in gamelogs]
        db.hths.insert(gamelogs)
        print self.player_code, self.player_code_2

    def stat_values_parser(self, cols, season):
        """
        Loops through of a list of columns and returns a list of values which
        change or skip the col strings based on their content.

        :param stat_values: Initial values list.
        :param cols: List of column values in a single gamelog.
        :param season: Season of the gamelog. Either 'regular' or 'playoff'.
        :returns: Parsed stat values.
        """
        stat_values = self.initialize_stat_values(season)
        for i, col in enumerate(cols):
            text = str(col.getText())
            # Date
            if i == 2:
                stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
            # Home
            elif i == 4:
                stat_values.append(False if text == '@' else True)
            # Percentages
            # Skip them because they can be calculated manually.
            elif i in {11, 14, 17}:
                pass
            # Number
            elif is_number(text):
                stat_values.append(float(text))
            # Text
            else:
                stat_values.append(text)
        return stat_values

    def update_hth_gamelog_keys(self, gamelog):
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
                Switches items containing Main with Opp in the header.

                :param title: Name to potentially replace.
                :returns: Replaced title.
                """
                if 'Main' in name:
                    return title.replace('Main', 'Opp')
                if 'Opp' in name:
                    return title.replace('Opp', 'Main')
                return title
            gamelog = {changer(key): val for key, val in gamelog.items()}
        return gamelog


def players_from_letter(letter):
        """
        Finds the home urls for all players whose last names start with a 
        particular letter.

        :param letter: Letter to find all players for.
        """
        br_url = 'http://www.basketball-reference.com'
        letter_page = requests.get(br_url + '/players/' + letter).text
        div_players = SoupStrainer('div', {'id': 'div_players'})
        soup = BeautifulSoup(letter_page, parse_only=div_players)

        def get_gamelog_urls(player_url):
            """
            Returns list of gamelog urls with every year for one player.

            :param player_url:
            :returns: All the links to seasons for a player.
            """
            page = requests.get(player_url).text
            all_totals = SoupStrainer('div', {'id': 'all_totals'})
            table_soup = BeautifulSoup(page, parse_only=all_totals)

            # Table containing player totals.
            totals_table = table_soup.find('table', {'id': 'totals'})
            # All single season tables.
            all_tables = totals_table.findAll('tr', {'class': 'full_table'})

            # Finds all links in all the season tables.
            return [
                br_url + link.get('href')
                for table in all_tables
                for link in table.find('td').findAll('a')
            ]

        # Current players are noted with bold text.
        current_names = soup.findAll('strong')

        # Adds a dict with keys Player, GamelogURLs and URL to players for each
        # current_player.
        players = []
        for n in current_names:
            name_data = next(n.children)
            name = name_data.contents[0]
            gamelog_urls = self.get_gamelog_urls(br_url +
                                                 name_data.attrs['href'])

            player = {
                'Player': name,
                'GamelogURLs': gamelog_urls,
                'URL': player_url
            }
            players.append(player)

        # Only inserts if there are any players for the letter.
        if players:
            db.players.insert(players)

class Creator(object):
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
        self.p = Pool(6)
        self.options = self.find_options()

    def find_options(self):
        """
        Finds a options to add to the database based on the collection.

        :returns: A list of potential options.
        """
        players = db.players.find()
        if self.collection == 'gamelogs':
            # If self.update only adds urls with 2015, else adds all urls.
            if self.update:
                return [
                    url
                    for p in players
                    for url in p['GamelogURLs']
                    if '2015' in url
                ]
            else:
                return [url for p in players for url in p['GamelogURLs']]
        if self.collection == 'hths':
            player_names = [find_player_code(p['Player']) for p in players]
            return list(combinations(player_names, 2))
        else:
            return 'abcdefghijklmnopqrstuvwxyz'

    def create(self):
        """
        Creates a complete collection in the database.
        """
        if self.collection == 'gamelogs':
            if self.update:
                # Deletes all gamelogs from current season.
                db.gamelogs.remove({'Year': 2015})
            f = lambda url: GamelogIngester(url).find_gamelogs()
            self.p.map(f, self.options)
        if self.collection == 'hths':
            f = lambda combo: HthIngester(combo).find_gamelogs()
            self.p.map(f, self.options)
        else:
            self.p.map(players_from_letter, self.options)
