from __future__ import (
    print_function, absolute_import, division, unicode_literals)

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
    def __init__(self, collection, **kwargs):
        """
        :param collection: Name of a collection in the nba database.
        :param url: Basketball-Reference url of player gamelogs for a single
            year.
        :param reg_table_id: Name of the regular season stats table in soup.
        :param playoff_table_id: Name of the playoff stats table in soup.
        :param player_code: Basketball-Reference code for one player.
        :param player_code_2: Basketball-Reference code for another player.
        :param payload: Payload for a Request.
        :returns: None if no header if found when the collection is
            'headtoheads', meaning the two players never played each other.

        POTENTIAL ERROR: What if player played in postseason but not reg?
        """
        self.collection = collection
        if self.collection == 'gamelogs':
            self.url = kwargs['url']
            self.reg_table_id = 'pgl_basic'
            self.playoff_table_id='pgl_basic_playoffs'
            self.page = requests.get(self.url).text
        else:
            self.url = ('http://www.basketball-reference.com/play-index/' +
                        'h2h_finder.cgi')
            self.player_code = kwargs['player_code']
            self.player_code_2 = kwargs['player_code_2']
            self.payload = {
                'p1': self.player_code,
                'p2': self.player_code_2,
                'request': 1
            }
            self.reg_table_id='stats_games'
            self.playoff_table_id='stats_games_playoffs'
            self.page = requests.get(self.url, params=self.payload).text
        self.soup = BeautifulSoup(
            self.page,
            parse_only=SoupStrainer('div', attrs={'id': 'page_content'}))
        self.reg_table = self.soup.find(
            'table', attrs={'id': self.reg_table_id})
        self.playoff_table = self.soup.find(
            'table', attrs={'id': self.playoff_table_id})
        self.header_add = utils.get_header(self.reg_table)
        if self.header_add:
            self.header = self.initialize_header()

    def find_gamelogs(self):
        """
        Adds all gamelogs from a basketball-reference url to the database.
        """
        # If no header, that means no matchups between a player combo exist.
        if not self.header_add:
            return None

        self.table_to_db('reg', self.reg_table)
        self.table_to_db('playoff', self.playoff_table)

    def initialize_header(self):
        """
        Creates the initial header list.

        :param collection: Name of a collection in the nba database.
        :param header_add: Header list created in get_header.
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

        :param collection: Name of a collection in the nba database.
        :param table: HTML table of gamelog stats for one year.
        :param header: Header of the gamelog table.
        :param season: Season of the gamelog. Either 'reg' or 'playoff'.
        :param url: Basketball-Reference url of player gamelogs for a year.
        :param player_code: Basketball-Reference code for one player.
        :param player_code_2: Basketball-Reference code for another player.
        """
        if not table:
            return None

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
            print(gamelogs)
        else:
            gamelogs = [
                self.update_headtohead_gamelog_keys(gamelog)
                for gamelog in gamelogs
            ]
            db.headtoheads.insert(gamelogs)
            print(gamelogs)

    def stat_values_parser(self, stat_values, cols):
        """
        :param collection: Name of a collection in the nba database.
        :param stat_values:
        :param cols:
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

        Try to make this with dictionary comprehension.
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


def gamelogs_from_url(url):
    """
    Finds all gamelogs from a basketball-reference gamelog url to add to
    the database.

    :param gamelog_url:
    """
    g = GamelogIngester('gamelogs', url=url)
    return g.find_gamelogs()


def create_gamelogs(update=True):
    """
    Calls gamelogs_from_url for all gamelog_urls. If update is True, only
    adds new gamelogs, else adds all gamelogs.
    """
    # Deletes all gamelogs from current season.
    if update is True:
        db.gamelogs.remove({'Year': 2015})

    urls = []
    for player in db.players.find():
        # If update only adds urls containing 2015, else adds all urls.
        if update is True:
            for url in player['GamelogURLs']:
                if '2015' in url:
                    urls.append(url)
        else:
            urls.extend(player['GamelogURLs'])

    p = Pool(8)
    for i, _ in enumerate(p.imap_unordered(gamelogs_from_url, urls), 1):
        sys.stderr.write('\rAdded: {0:%}'.format(i/len(urls)))


def headtoheads_from_combo(player_combination):
    """
    Adds all headtohead gamelogs between two players to the database given
    two player names in 'FirstName LastName' format.

    :param player_combination: Tuple of player_code and player_code_2.
    """
    player_code, player_code_2 = player_combination

    g = GamelogIngester(
        'headtoheads', player_code=player_code, player_code_2=player_code_2)
    return g.find_gamelogs()


def create_headtoheads():
    """
    Calls headtoheads_from_url for all combinations of two active players.
    """
    all_players = db.players.find({})
    player_names = [
        utils.find_player_code(player['Player'])
        for player in all_players
    ]

    player_combos = list(combinations(player_names, 2))

    p = Pool(8)
    for i, _ in enumerate(
            p.imap_unordered(headtoheads_from_combo, player_combos), 1):
        sys.stderr.write('\rAdded: {0:%}'.format(i/len(player_combos)))


def players_from_letter(letter):
    br_url = 'http://www.basketball-reference.com'
    letter_page = requests.get(br_url + '/players/%s/' % (letter)).text
    soup = BeautifulSoup(
        letter_page,
        parse_only=SoupStrainer('div', attrs={'id': 'div_players'}))

    players = []
    current_names = soup.findAll('strong')
    for n in current_names:
        name_data = next(n.children)
        name = name_data.contents[0]
        player_url = br_url + name_data.attrs['href']
        gamelog_urls = get_gamelog_urls(player_url)

        player = dict(
            Player=name,
            GamelogURLs=gamelog_urls,
            URL=player_url)
        players.append(player)

    db.players.insert(players)


def get_gamelog_urls(player_url):
    """
    Returns list of gamelog urls with every year for one player.
    """
    page = requests.get(player_url).text
    table_soup = BeautifulSoup(
        page, parse_only=SoupStrainer('div', attrs={'id': 'all_totals'}))

    # Table containing player totals.
    totals_table = table_soup.find('table', attrs={'id': 'totals'})
    # All single season tables.
    all_tables = totals_table.findAll('tr', attrs={'class': 'full_table'})

    return [
        'http://www.basketball-reference.com' + link.get("href")
        for table in all_tables
        for link in table.find('td').findAll("a")
    ]


def create_players():
    """
    Creates a collection of player data for all active players.
    """
    p = Pool(8)
    letters = string.ascii_lowercase
    for i, _ in enumerate(
            p.imap_unordered(get_player, letters), 1):
        sys.stderr.write('\rAdded: {0:%}'.format(i/len(letters)))
