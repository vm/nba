import asyncio
import os
import re
import string
import sys
from datetime import datetime
from itertools import combinations

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

from . import utils
from .app import db

sem = asyncio.Semaphore(10)


@asyncio.coroutine
def get(url, **kwargs):
    r = yield from aiohttp.request('GET', url, **kwargs)
    return (yield from r.read_and_close())


@asyncio.coroutine
def find_gamelogs(
        collection, url, reg_table_id, playoff_table_id, player_code=None,
        player_code_2=None, payload=None):
    """
    Adds all gamelogs from a basketball-reference url to the database.

    :param collection: Name of a collection in the nba database.
    :param url: Basketball-Reference url of player gamelogs for a single year.
    :param reg_table_id: Name of the regular season stats table in soup.
    :param playoff_table_id: Name of the playoff stats table in soup.
    :param player_code: Basketball-Reference code for one player.
    :param player_code_2: Basketball-Reference code for another player.
    :param payload: Payload for a Request.
    :returns: None if no header if found when the collection is
        'headtoheads', meaning the two players never played each other.
    """
    # Only hth_url requires a payload.
    with (yield from sem):
        page = yield from get(url)

    soup = BeautifulSoup(
        page, parse_only=SoupStrainer('div', attrs={'id': 'page_content'}))

    reg_table = soup.find('table', attrs={'id': reg_table_id})
    playoff_table = soup.find('table', attrs={'id': playoff_table_id})

    # Initializes header based on the collection.
    header_add = utils.get_header(reg_table)
    # Only adds gamelogs to database if a header is found.
    # If no header, that means there are no matchups between a player combo.
    if header_add:
        header = initialize_header(collection, header_add)
    else:
        return None

    if collection == 'gamelogs':
        # Adds all gamelogs in regular season table to database.
        table_to_db(
            collection='gamelogs', table=reg_table, header=header,
            season='reg', url=url)
        # Adds all gamelogs in playoff table to database.
        table_to_db(
            collection='gamelogs', table=playoff_table,
            header=header, season='playoff', url=url)
    else:
        # Adds all gamelogs in regular season table to database.
        table_to_db(
            collection='headtoheads', table=reg_table,
            header=header, season='reg', player_code=player_code,
            player_code_2=player_code_2)
        # Adds all gamelogs in playoff table to database.
        table_to_db(
            collection='headtoheads', table=playoff_table,
            header=header, season='playoff', player_code=player_code,
            player_code_2=player_code_2)


def initialize_header(collection, header_add):
    if collection == 'gamelogs':
        header = ['Player', 'PlayerCode', 'Year', 'Season'] + header_add
        header[9] = 'Home'  # Replaces empty column title.
        header.insert(11, 'WinLoss')  # Inserts missing column title.
    else:
        header = (['MainPlayer', 'MainPlayerCode', 'OppPlayer',
                   'OppPlayerCode', 'Season'] +
                  header_add)
        header[9] = 'Home'  # Replaces empty column.
        header.insert(11, 'WinLoss')  # Inserts missing column.

    # Remove all percentages
    remove_items = ['FGP', 'FTP', 'TPP']
    for item in sorted(remove_items, reverse=True):
        header.remove(item)

    return header

def table_to_db(
        collection, table, header, season, url=None, player_code=None,
        player_code_2=None):
    """
    Adds all gamelogs in a table to the database.

    :param collection: Name of a collection in the nba database.
    :param table: HTML table of gamelog stats for one year.
    :param header: Header of the gamelog table.
    :param season: Season of the gamelog. Either 'reg' or 'playoff'.
    :param url: Basketball-Reference url of player gamelogs for a single year.
    :param player_code: Basketball-Reference code for one player.
    :param player_code_2: Basketball-Reference code for another player.
    """
    if not table:
        return None

    rows = [r for r in table.findAll('tr')[1:] if len(r.findAll('td')) > 0]

    # Each row is one gamelog.
    for row in rows:
        if collection == 'gamelogs':
            path_components = utils.path_components_of_url(url)
            stat_values = [
                utils.find_player_name(path_components[3]),  # Player
                path_components[3],  # PlayerCode
                path_components[5],  # Year
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
        cols = row.findAll('td')
        stat_values = stat_values_parser(collection, stat_values, cols)

        # Zips the each header item and stat value together and adds each into
        # a dictionary, creating a dict of gamelog stats for one game.
        gamelog = dict(list(zip(header, stat_values)))

        if collection == 'gamelogs':
            db.gamelogs.insert(gamelog)
            print(url)
        else:
            update_headtohead_gamelog_keys(gamelog)
            db.headtoheads.insert(gamelog)


def stat_values_parser(collection, stat_values, cols):
    for i, col in enumerate(cols):
        text = str(col.getText())
        # Date
        if i == 2:
            stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
        # Home
        elif ((collection == 'gamelogs' and i == 5) or
              (collection == 'headtoheads' and i == 4)):
            stat_values.append(False if text == '@' else True)
        # WinLoss
        elif collection == 'gamelogs' and i == 7:
            plusminus = re.compile(".*?\((.*?)\)")
            stat_values.append(float(plusminus.match(text).group(1)))
        # Percentages
        # Skip them because they can be calculated manually.
        elif ((collection == 'gamelogs' and i in {12, 15, 18}) or
              (collection == 'headtoheads' and i in {11, 14, 17})):
            pass
        # PlusMinus
        elif collection == 'gamelogs' and i == 29:
            stat_values.append(0 if text == '' else float(text))
        # Number
        elif utils.is_number(text):
            stat_values.append(float(text))
        # Text
        else:
            stat_values.append(text)
    return stat_values


def update_headtohead_gamelog_keys(gamelog):
    """
    Removes Player key and switches MainPlayerCode and OppPlayerCode keys if
    the MainPlayerCode is not player_code.

    Try to make this with dictionary comprehension.
    """
    gamelog.pop('Player', None)
    if player_code != gamelog['MainPlayerCode']:
        gamelog['MainPlayerCode'] = gamelog.pop('OppPlayerCode')
        gamelog['OppPlayerCode'] = gamelog.pop('MainPlayerCode')
        gamelog['MainPlayer'] = gamelog.pop('OppPlayer')
        gamelog['OppPlayer'] = gamelog.pop('MainPlayer')
    return gamelog


def gamelogs_from_url(gamelog_url):
    """
    Finds all gamelogs from a basketball-reference gamelog url to add to
    the database.

    :param gamelog_url:
    """
    return find_gamelogs(
        collection='gamelogs', url=gamelog_url, reg_table_id='pgl_basic',
        playoff_table_id='pgl_basic_playoffs')


def create_gamelogs_collection(update=True):
    """
    Calls gamelogs_from_url for all gamelog_urls. If update is True, only
    adds new gamelogs, else adds all gamelogs.
    """
    # Deletes all gamelogs from current season.
    if update:
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

    loop = asyncio.get_event_loop()
    tasks = [gamelogs_from_url(url) for url in urls]
    loop.run_until_complete(asyncio.wait(tasks))


def headtoheads_from_combo(player_combination):
    """
    Adds all headtohead gamelogs between two players to the database given
    two player names in 'FirstName LastName' format.

    :param player_combination: Tuple of player_code and player_code_2.
    """
    player_code, player_code_2 = player_combination
    payload = {'p1': player_code, 'p2': player_code_2, 'request': 1}
    hth_url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'

    return find_gamelogs(
        collection='headtoheads', url=hth_url,
        reg_table_id='stats_games', playoff_table_id='stats_games_playoffs',
        player_code=player_code, player_code_2=player_code_2,
        payload=payload)


def create_headtoheads_collection():
    """
    Calls headtoheads_from_url for all combinations of two active players.
    """
    all_players = db.players.find({})
    player_names = [
        utils.find_player_code(player['Player'])
        for player in all_players
    ]

    player_combos = list(combinations(player_names, 2))

    loop = asyncio.get_event_loop()
    tasks = [headtoheads_from_combo(combo) for combo in player_combos]
    loop.run_until_complete(asyncio.wait(tasks))


@asyncio.coroutine
def players_from_letter(letter):
    br_url = 'http://www.basketball-reference.com'
    with (yield from sem):
        letter_page = yield from get(br_url + '/players/%s/' % (letter))
    soup = BeautifulSoup(
        letter_page,
        parse_only=SoupStrainer('div', attrs={'id': 'div_players'}))

    current_names = soup.findAll('strong')
    for n in current_names:
        name_data = next(n.children)
        name = name_data.contents[0]
        player_url = br_url + name_data.attrs['href']
        gamelog_urls = yield from get_gamelog_urls(player_url)

        player = dict(
            Player=name,
            GamelogURLs=gamelog_urls,
            URL=player_url)

        db.players.insert(player)
        print(name)


@asyncio.coroutine
def get_gamelog_urls(player_url):
    """
    Returns list of gamelog urls with every year for one player.
    """
    with (yield from sem):
        page = yield from get(player_url)
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


def create_players_collection():
    """
    Creates a collection of player data for all active players.
    """
    loop = asyncio.get_event_loop()
    tasks = [players_from_letter(letter) for letter in string.ascii_lowercase]
    loop.run_until_complete(asyncio.wait(tasks))


def create(collection, update=False):
    if collection == 'players':
        create_players_collection()
    elif collection == 'gamelogs':
        create_gamelogs_collection(update)
    else:
        create_headtoheads_collection()


def remove_all(collection):
    if collection == 'players':
        db.players.remove({})
    elif collection == 'gamelogs':
        db.gamelogs.remove({})
    else:
        db.headtoheads.remove({})
    print(('Removed ' + collection + '.'))
