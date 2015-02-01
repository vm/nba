from __future__ import division

import os
import string
import sys
from datetime import datetime
from itertools import combinations, izip
from multiprocessing import Pool

from pymongo import MongoClient

import utils
from . import app

connection = MongoClient(app.config['MONGODB_SETTINGS']['host'])


def find_gamelogs(
        collection_id, url, reg_table_id, playoff_table_id, player_code=None,
        player_code_2=None, payload=None):
    """
    Adds all gamelogs from a basketball-reference url to the database.

    :param collection_id: Collection in the nba database.
    :param url: Basketball-Reference url of player gamelogs for a single year.
    :param reg_table_id: Name of the regular season stats table in table_soup.
    :param playoff_table_id: Name of the playoff stats table in table_soup.
    :param player_code: Basketball-Reference code for one player.
    :param player_code_2: Basketball-Reference code for another player.
    :param payload: Payload for a Request.
    :returns: None if no header if found when the collection_id is
        'headtoheads', which means the two players never played each other.
    """
    # Only headtohead_url requires a payload.
    table_soup = utils.soup_from_url(url, payload)

    reg_table = table_soup.find('table', attrs={'id': reg_table_id})
    playoff_table = table_soup.find('table', attrs={'id': playoff_table_id})

    # Initializes header based on the collection_id.
    if collection_id == 'gamelogs':
        gamelog_header = (['Player', 'PlayerCode', 'Year', 'Season'] +
                          utils.get_header(reg_table))
        gamelog_header[9] = 'HomeAway'  # Replaces empty column title.
        gamelog_header.insert(11, 'WinLoss')  # Inserts missing column title.

        remove_items = ['FGP', 'FTP', 'TPP']
        for item in sorted(remove_items, reverse=True):
            gamelog_header.remove(item)

        # Adds all gamelogs in regular season table to database.
        table_to_db(
            collection_id='gamelogs', table=reg_table, header=gamelog_header,
            season='reg', url=url)
        # Adds all gamelogs in playoff table to database.
        table_to_db(
            collection_id='gamelogs', table=playoff_table,
            header=gamelog_header, season='playoff', url=url)
    else:
        hth_header_add = utils.get_header(reg_table)

        # Only adds gamelogs to database if a header is found.
        # If no header, that means there are no matchups between the players.
        if hth_header_add:
            hth_header = (['MainPlayer', 'MainPlayerCode', 'OppPlayer',
                           'OppPlayerCode', 'Season'] +
                          hth_header_add)
            hth_header[9] = 'HomeAway'  # Replaces empty column.
            hth_header.insert(11, 'WinLoss')  # Inserts missing column.

            # Remove all percentages
            remove_items = ['FGP', 'FTP', 'TPP']
            for item in sorted(remove_items, reverse=True):
                hth_header.remove(item)

            # Adds all gamelogs in regular season table to database.
            table_to_db(
                collection_id='headtoheads', table=reg_table,
                header=hth_header, season='reg', player_code=player_code,
                player_code_2=player_code_2)
            # Adds all gamelogs in playoff table to database.
            table_to_db(
                collection_id='headtoheads', table=playoff_table,
                header=hth_header, season='playoff', player_code=player_code,
                player_code_2=player_code_2)
        else:
            return None


def gamelogs_from_url(gamelog_url):
    """
    Finds all gamelogs from a basketball-reference gamelog url to add to
    the database.

    :param gamelog_url:
    """
    return find_gamelogs(
        collection_id='gamelogs', url=gamelog_url, reg_table_id='pgl_basic',
        playoff_table_id='pgl_basic_playoffs')


def headtoheads_from_combination(player_combination):
    """
    Adds all headtohead gamelogs between two players to the database given
    two player names in 'FirstName LastName' format.

    :param player_combination: Tuple of player_code and player_code_2.
    """
    player_code, player_code_2 = player_combination
    payload = {
        'p1': player_code, 'p2': player_code_2, 'request': 1
    }
    headtohead_url = ('http://www.basketball-reference.com/play-index/' +
                      'h2h_finder.cgi')

    return find_gamelogs(
        collection_id='headtoheads', url=headtohead_url,
        reg_table_id='stats_games', playoff_table_id='stats_games_playoffs',
        player_code=player_code, player_code_2=player_code_2,
        payload=payload)


def table_to_db(
        collection_id, table, header, season, url=None, player_code=None,
        player_code_2=None):
    """
    Adds all gamelogs in a table to the database.

    :param collection_id: Name of a collection in the nba database.
    :param table: HTML table of gamelog stats for one year.
    :param header: Header of the gamelog table.
    :param season: Season of the gamelog. Either 'reg' or 'playoff'.
    :param url: Basketball-Reference url consisting of gamelogs for a single
        year of player stats.
    :param player_code: Player code whose stats are returned.
    :param player_code_2: Opponent player code of opponent.
    """
    if not table:
        return None

    rows = table.findAll('tr')[1:]
    rows = [r for r in rows if len(r.findAll('td')) > 0]  # Removes header.

    # Each row is one gamelog.
    for row in rows:
        if collection_id == 'gamelogs':
            path_components = utils.path_components_of_url(url)
            stat_values = [
                utils.find_player_name(str(path_components[3])),  # Player
                str(path_components[3]),  # PlayerCode
                int(path_components[5]),  # Year
                season  # Season
            ]
        else:
            stat_values = [
                utils.find_player_name(player_code),  # MainPlayer
                player_code,  # MainPlayerCode
                utils.find_player_name(player_code_2),  # OppPlayer
                player_code_2,  # OppPlayerCode
                season  # Season
            ]

        # Each column is one stat type.
        for col_num, col in enumerate(row.findAll('td')):
            text = str(col.getText())

            # Stat values are converted by position based on the collection.
            if collection_id == 'gamelogs':
                if col_num == 2:  # Date
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                elif col_num in {12, 15, 18}:  # Percentages
                    pass  # Skip percentages, can be manually calculated.
                elif col_num == 29:  # PlusMinus
                    stat_values.append(0 if text == '' else float(text))
                elif utils.is_number(text):  # Number
                    stat_values.append(float(text))
                else:
                    stat_values.append(text)
            if collection_id == 'headtoheads':
                if col_num == 2:  # Date
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                elif col_num in {11, 14, 17}:  # Percentages
                    pass  # Skip percentages, can be manually calculated.
                elif utils.is_number(text):
                    stat_values.append(float(text))  # Number
                else:
                    stat_values.append(text)

        # Zips the each header item and stat value together and adds each into
        # a dictionary, creating a dict of gamelog stats for one game.
        gamelog = dict(izip(header, stat_values))

        # Removes Player key and switches MainPlayerCode and OppPlayerCode
        # keys if the MainPlayerCode is not player_code.
        if collection_id == 'headtoheads':
            gamelog.pop('Player', None)
            if player_code != gamelog['MainPlayerCode']:
                gamelog['MainPlayerCode'] = gamelog.pop('OppPlayerCode')
                gamelog['OppPlayerCode'] = gamelog.pop('MainPlayerCode')
                gamelog['MainPlayer'] = gamelog.pop('OppPlayer')
                gamelog['OppPlayer'] = gamelog.pop('MainPlayer')

        if collection_id == 'gamelogs':
            connection.nba.gamelogs.insert(gamelog)
        else:
            connection.nba.headtoheads.insert(gamelog)


def create_gamelogs_collection(update=True):
    """
    Calls gamelogs_from_url for all gamelog_urls. If update is True, only
    adds new gamelogs, else adds all gamelogs.
    """
    # Deletes all gamelogs from current season.
    if update is True:
        connection.nba.gamelogs.remove({'Year': 2015})

    urls = []
    for player in connection.nba.players.find():
        # If update only adds urls containing 2015, else adds all urls.
        if update is True:
            for url in player['GamelogURLs']:
                if '2015' in url:
                    urls.append(url)
        else:
            urls.extend(player['GamelogURLs'])

    p = Pool(20)
    for i, _ in enumerate(p.imap_unordered(gamelogs_from_url, urls), 1):
        sys.stderr.write('\rAdded: {0:%}'.format(i/len(urls)))


def create_headtoheads_collection():
    """
    Calls headtoheads_from_url for all combinations of two active players.
    """
    all_players = connection.nba.players.find({})
    player_names = [
        utils.find_player_code(player['Player'])
        for player in all_players
    ]

    player_combos = list(combinations(player_names, 2))

    p = Pool(20)
    for i, _ in enumerate(
            p.imap_unordered(headtoheads_from_combination, player_combos), 1):
        sys.stderr.write('\rAdded: {0:%}'.format(i/len(player_combos)))


def create_players_collection():
    """
    Creates a collection of player data for all active players.
    """
    br_url = 'http://www.basketball-reference.com'

    for letter in string.ascii_lowercase:
        letter_page = utils.soup_from_url(br_url + '/players/%s/' % (letter))

        current_names = letter_page.findAll('strong')
        for n in current_names:
            name_data = n.children.next()
            name = name_data.contents[0]
            player_url = br_url + name_data.attrs['href']
            gamelog_urls = utils.get_gamelog_urls(player_url)

            player = dict(
                Player=name,
                GamelogURLs=gamelog_urls,
                URL=player_url)

            connection.nba.players.insert(player)
