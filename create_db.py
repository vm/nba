import json

from bson.json_util import dumps
from datetime import datetime
from itertools import combinations, izip

from database import connection, db
from utils import (find_player_code, get_header, is_number, open_file,
                   path_list_from_url, soup_from_url)


def games_from_url(
        collection, url, reg_id, playoff_id, p1_code=False, p2_code=False,
        payload=False):
    """
    Make a list of dictionaries from a given basketball-reference url.

    Scrape a url and finds tables for regular season and playoff statistics.
    Create a dictionary for each row in the table (representing one game). The
    dictionaries contain keys for each stat type in the table header.

    Header is initialized with Player, Year and Season as they are not found
    on the table, to which the found header is appended. The header also does
    not properly contain 'HomeAway' and 'WinLoss', so they are added manually.

    If there is a regular list but no playoff list, only the regular list is
    returned, or vice versa. If both exist, returns a concatenated list of
    both.
    """

    if payload is not False:
        table_soup = soup_from_url(url, payload)
    else:
        table_soup = soup_from_url(url)

    reg_table = table_soup.find(
        'table', attrs={'id': reg_id})
    playoff_table = table_soup.find(
        'table', attrs={'id': playoff_id})

    if collection == 'gamelogs':
        gamelog_header = ([u'Player', u'Year', u'Season'] +
                          get_header(reg_table))
        gamelog_header[8] = u'HomeAway'
        gamelog_header.insert(10, u'WinLoss')

        reg_dict = table_to_dict(
            'gamelogs', reg_table, gamelog_header, season='reg', url=url)
        playoff_dict = table_to_dict(
            'gamelogs', playoff_table, gamelog_header, season='playoff',
            url=url)
    else:
        hth_header_add = get_header(reg_table)

        if hth_header_add:
            hth_header = [u'p1', u'p2', u'Season'] + hth_header_add
            hth_header[8] = u'HomeAway'
            hth_header.insert(10, u'WinLoss')

            table_to_dict(
                'headtoheads', reg_table, hth_header, season='reg',
                p1_code=p1_code, p2_code=p2_code)
            table_to_dict(
                'headtoheads', playoff_table, hth_header, season='playoff',
                p1_code=p1_code, p2_code=p2_code)
        else:
            return None

    return "Done."


def gamelogs_from_url(url):
    return games_from_url(
        'gamelogs', url, 'pgl_basic', 'pgl_basic_playoffs')


def hths_from_url(p1, p2):
    p1_code = find_player_code(p1)
    p2_code = find_player_code(p2)

    payload = {'p1': p1_code, 'p2': p2_code, 'request': 1}
    hth_url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'

    return games_from_url(
        'headtoheads', hth_url, 'stats_games', 'stats_games_playoffs',
        p1_code, p2_code, payload)


def table_to_dict(
        collection_id, table, header, season, url=False, p1_code=False,
        p2_code=False):

    if not table:
        return None

    rows = table.findAll('tr')[1:]
    rows = [r for r in rows if len(r.findAll('td')) > 0]

    for row in rows:
        if collection_id == 'gamelogs':
            path_list = path_list_from_url(url)
            vals = [str(path_list[3]), int(path_list[5]), season]
        else:
            vals = [p1_code, p2_code, season]

        for col_num, col in enumerate(row.findAll('td')):
            text = str(col.getText())

            if collection_id == 'gamelogs':
                # Date
                if col_num == 2:
                    vals.append(datetime.strptime(text, '%Y-%m-%d'))
                # Percentages
                elif col_num == 12 or col_num == 15 or col_num == 18:
                    vals.append(0.0 if text == '' else float(text))
                # PlusMinus
                elif col_num == 29:
                    vals.append('0' if text == '' else text)
                elif is_number(text):
                    vals.append(float(text))
                else:
                    vals.append(text)
            else:
                # Percentages
                if col_num == 14 or col_num == 17 or col_num == 20:
                    vals.append(0.0 if text == '' else float(text))
                elif is_number(text):
                    vals.append(float(text))
                else:
                    vals.append(text)

        # single_season_list.append(dict(izip(header, vals)))
        collection = connection[collection_id].users
        collection.insert(dict(izip(header, vals)))

    return 'All gamelogs added.'


def create_gamelog_collection():
    """
    Concatenate all the lists of player gamelogs into one list and saves as a
    JSON file.
    """

    gamelog_urls = open_file('./gamelog_urls')

    for num, url in enumerate(gamelog_urls):
        print (str(((num + 1) * 100) / (len(gamelog_urls))) +
               '%  --  ' +
               url)
        gamelogs_from_url(url)

    return 'ALL GAMELOGS ADDED.'


def create_hth_collection():
    """
    Concatenate all the lists of headtohead gamelogs into one list and save as
    a JSON file.
    """

    player_names_urls = open_file('./player_names_urls.json')

    player_names = []
    for name, url in player_names_urls.items():
        player_names.append(name)

    all_hth_dict = []
    player_combinations = list(combinations(player_names, 2))

    for num, c in enumerate(combinations):
        print c
        hths_from_url(*c)

    return 'ALL HTHS ADDED.'
