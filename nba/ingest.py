from __future__ import (print_function, absolute_import, division,
                        unicode_literals)

import os
import re
import string
import sys
from datetime import datetime
from itertools import combinations
from multiprocessing import Pool

import requests
from bs4 import BeautifulSoup, SoupStrainer

from . import utils
from .app import db


class GamelogIngester(object):
    """
    Adds all the gamelogs on a particular page to the database.
    """
    def __init__(self, collection, url=None, player_combination=None,
                 output=False):
        """
        :param collection: Name of a collection in the nba database.
        :param url: (optional) Basketball-Reference url for a single year
            of gamelogs for a player to add to gamelogs collection.
        :param player_combination: (optional) Basketball-Reference codes for
            two players used to add to headtoheads collection.
        :param output: (optional) Whether to print progress or not.
        """
        # General
        self.collection = collection
        self.output = output

        # Based on collection
        if self.collection == 'gamelogs':
            self.url = url
            self.reg_table_id = 'pgl_basic'
            self.playoff_table_id = 'pgl_basic_playoffs'
            self.page = requests.get(self.url).text
        else:
            self.url = ('http://www.basketball-reference.com/play-index/' +
                        'h2h_finder.cgi')
            self.player_code, self.player_code_2 = player_combination
            self.payload = {
                'p1': self.player_code,
                'p2': self.player_code_2,
                'request': 1
            }
            self.reg_table_id='stats_games'
            self.playoff_table_id='stats_games_playoffs'
            self.page = requests.get(self.url, params=self.payload).text

        # Scraping
        page_content = SoupStrainer('div', {'id': 'page_content'})
        self.soup = BeautifulSoup(self.page, parse_only=page_content)
        self.reg_table = self.soup.find('table',
                                        {'id': self.reg_table_id})
        self.playoff_table = self.soup.find('table',
                                            {'id': self.playoff_table_id})

        # Header
        self.header_add = utils.get_header(self.reg_table)
        if self.header_add:
            self.header = self.initialize_header()

    def find_gamelogs(self):
        """
        Adds all gamelogs from a basketball-reference url to the database.
        """
        # If no header, that means no matchups between a player combo exist.
        if not self.header_add:
            return

        self.table_to_db('reg', self.reg_table)
        self.table_to_db('playoff', self.playoff_table)

    def initialize_header(self):
        """
        Creates the initial header list.
        """
        if self.collection == 'gamelogs':
            header = (['Player', 'PlayerCode', 'Year', 'Season'] +
                      self.header_add)
        else:
            header = (['MainPlayer', 'MainPlayerCode', 'OppPlayer',
                       'OppPlayerCode', 'Season'] +
                      self.header_add)

        header[9] = 'Home'  # Replaces empty column.
        header.insert(11, 'WinLoss')  # Inserts missing column.

        # Remove all percentages
        remove_items = ['FGP', 'FTP', 'TPP']
        for item in sorted(remove_items, reverse=True):
            header.remove(item)

        return header

    def table_to_db(self, season, table):
        """
        Adds all gamelogs in a table to the database.

        :param season: Season of the gamelog. Either 'reg' or 'playoff'.
        :param table: Table of gamelog stats for one year.
        """
        if not table:
            return

        rows = table.findAll('tr')
        del rows[0]

        # Each row is one gamelog.
        gamelogs = []
        for row in rows:
            cols = row.findAll('td')
            if not cols:
                continue

            if self.collection == 'gamelogs':
                path_components = utils.path_components_of_url(self.url)
                stat_values = [
                    utils.find_player_name(path_components[3]),  # Player
                    path_components[3],  # PlayerCode
                    path_components[5],  # Year
                    season  # Season
                ]
            else:
                stat_values = [
                    utils.find_player_name(self.player_code),  # MainPlayer
                    self.player_code,  # MainPlayerCode
                    utils.find_player_name(self.player_code_2),  # OppPlayer
                    self.player_code_2,  # OppPlayerCode
                    season  # Season
                ]

            # Each column is one stat type.
            stat_values = self.stat_values_parser(stat_values, cols)

            # Zips the each header item and stat value together and adds each
            # into a dictionary, creating a dict of gamelog stats for a game.
            gamelog = dict(zip(self.header, stat_values))
            gamelogs.append(gamelog)

        if self.collection == 'gamelogs':
            db.gamelogs.insert(gamelogs)
            if self.output:
                print(self.url)
        else:
            gamelogs = [
                self.update_headtohead_gamelog_keys(gamelog)
                for gamelog in gamelogs
            ]
            db.headtoheads.insert(gamelogs)
            if self.output:
                print(self.player_code, self.player_code_2)

    def stat_values_parser(self, stat_values, cols):
        """
        Loops through of a list of columns and returns a list of values
        which change or skip the col strings based on their content.

        :param stat_values: Initial values list.
        :param cols: List of column values in a single gamelog.
        """
        for i, col in enumerate(cols):
            text = str(col.getText())
            # Date
            if i == 2:
                stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
            # Home
            elif ((self.collection == 'gamelogs' and i == 5) or
                  (self.collection == 'headtoheads' and i == 4)):
                stat_values.append(False if text == '@' else True)
            # WinLoss
            elif self.collection == 'gamelogs' and i == 7:
                plusminus = re.compile(".*?\((.*?)\)")
                stat_values.append(float(plusminus.match(text).group(1)))
            # Percentages
            # Skip them because they can be calculated manually.
            elif ((self.collection == 'gamelogs' and i in {12, 15, 18}) or
                  (self.collection == 'headtoheads' and i in {11, 14, 17})):
                pass
            # PlusMinus
            elif self.collection == 'gamelogs' and i == 29:
                stat_values.append(0 if text == '' else float(text))
            # Number
            elif utils.is_number(text):
                stat_values.append(float(text))
            # Text
            else:
                stat_values.append(text)
        return stat_values

    def update_headtohead_gamelog_keys(self, gamelog):
        """
        Removes Player key and switches MainPlayerCode and OppPlayerCode keys
        if the MainPlayerCode is not player_code.

        :param gamelog:
        """
        gamelog.pop('Player', None)
        if self.player_code != gamelog['MainPlayerCode']:
            def changer(name):
                if 'Main' in name:
                    return name.replace('Main', 'Opp')
                if 'Opp' in name:
                    return name.replace('Opp', 'Main')
                return name
            gamelog = {changer(key): val for key, val in gamelog.items()}
        return gamelog


def gamelogs_from_url(gamelog_url):
    """
    Finds all gamelogs from a basketball-reference gamelog url to add to
    the database.

    :param gamelog_url:
    """
    g = GamelogIngester('gamelogs', url=gamelog_url)
    return g.find_gamelogs()


def headtoheads_from_combo(player_combination):
    """
    Adds all headtohead gamelogs between two players to the database given
    two player names in 'FirstName LastName' format.

    :param player_combination: Tuple of player_code and player_code_2.
    """
    g = GamelogIngester('headtoheads', player_combination=player_combination)
    return g.find_gamelogs()


def players_from_letter(letter):
    """
    Finds the home urls for all players whose last names start with a
    a particular letter.

    :param letter: Letter to find all players for.
    """
    br_url = 'http://www.basketball-reference.com'
    letter_page = requests.get(br_url + '/players/%s/' % (letter)).text
    div_players = SoupStrainer('div', {'id': 'div_players'})
    soup = BeautifulSoup(letter_page, parse_only=div_players)

    def get_gamelog_urls(player_url):
        """
        Returns list of gamelog urls with every year for one player.

        :param player_url:
        """
        page = requests.get(player_url).text
        all_totals = SoupStrainer('div', {'id': 'all_totals'})
        table_soup = BeautifulSoup(page, parse_only=all_totals)

        # Table containing player totals.
        totals_table = table_soup.find('table', {'id': 'totals'})
        # All single season tables.
        all_tables = totals_table.findAll('tr', {'class': 'full_table'})

        return [
            'http://www.basketball-reference.com' + link.get("href")
            for table in all_tables
            for link in table.find('td').findAll("a")
        ]

    players = []
    current_names = soup.findAll('strong')
    for n in current_names:
        name_data = next(n.children)
        name = name_data.contents[0]
        player_url = br_url + name_data.attrs['href']
        gamelog_urls = get_gamelog_urls(player_url)
        player = {
            'Player': name,
            'GamelogURLs': gamelog_urls,
            'URL': player_url
        }
        players.append(player)
    db.players.insert(players)


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
        self.p = Pool(8)
        self.options = self.find_options()

    def find_options(self):
        """
        Finds a options to add to the database based on the collection.

        :returns: A list of potential options.
        """
        if self.collection == 'gamelogs':
            # If self.update only adds urls with 2015, else adds all urls.
            if self.update:
                return [
                    url
                    for player in db.players.find()
                    for url in player['GamelogURLs']
                    if '2015' in url
                ]
            else:
                return [
                    url
                    for player in db.players.find()
                    for url in player['GamelogURLs']
                ]

        elif self.collection == 'headtoheads':
            all_players = db.players.find()
            player_names = [
                utils.find_player_code(player['Player'])
                for player in all_players
            ]
            return list(combinations(player_names, 2))

        else:
            return string.ascii_lowercase

    def map_call(self, func):
        """
        Maps a function which adds items to a collection and prints the
        percentage progress.

        :func: The function to map.
        """
        for i, _ in enumerate(self.p.imap_unordered(func, self.options), 1):
            sys.stderr.write('\r{0:.{1}%}'.format(i/len(self.options), 2))

    def create(self):
        """
        Creates a complete collection in the database.
        """
        if self.collection == 'gamelogs':
            if self.update:
                # Deletes all gamelogs from current season.
                db.gamelogs.remove({'Year': 2015})
            self.map_call(gamelogs_from_url)
        elif self.collection == 'headtoheads':
            self.map_call(headtoheads_from_combo)
        else:
            self.map_call(players_from_letter)
