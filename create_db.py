from datetime import datetime
from itertools import combinations, izip

from database import db, app
from utils import (
    find_player_code, get_header, is_number, open_file, path_list_from_url,
    soup_from_url)


def games_from_url(
        collection_id, url, reg_id, playoff_id, p1_code=False, p2_code=False,
        payload=False):
    """
    Adds each gamelog from a given basketball-reference url to the database.

    Scrapes a url and finds tables for regular season and playoff statistics
    and creates a dictionary for each row (each representing one game). The
    dictionaries contain keys for each stat type in the table header.

    The header is initialized with u'Player', u'Year' and u'Season' if
    collection_id is 'gamelogs' or u'p1', 'p2', u'Season' if 'headtoheads' as
    they are not found on the table. This is appended to the header found on
    the table. The header also does not properly contain u'HomeAway' and
    u'WinLoss', so they are added manually.
    """

    if payload is not False:
        table_soup = soup_from_url(url, payload)
    else:
        table_soup = soup_from_url(url)

    reg_table = table_soup.find(
        'table', attrs={'id': reg_id})
    playoff_table = table_soup.find(
        'table', attrs={'id': playoff_id})

    if collection_id == 'gamelogs':
        gamelog_header = ([u'Player', u'Year', u'Season'] +
                          get_header(reg_table))
        gamelog_header[8] = u'HomeAway'
        gamelog_header.insert(10, u'WinLoss')

        reg_dict = add_table_to_db(
            'gamelogs', reg_table, gamelog_header, season='reg', url=url)
        playoff_dict = add_table_to_db(
            'gamelogs', playoff_table, gamelog_header, season='playoff',
            url=url)
    else:
        hth_header_add = get_header(reg_table)

        if hth_header_add:
            hth_header = [u'p1', u'p2', u'Season'] + hth_header_add
            hth_header[8] = u'HomeAway'
            hth_header.insert(10, u'WinLoss')

            add_table_to_db(
                'headtoheads', reg_table, hth_header, season='reg',
                p1_code=p1_code, p2_code=p2_code)
            add_table_to_db(
                'headtoheads', playoff_table, hth_header, season='playoff',
                p1_code=p1_code, p2_code=p2_code)
        else:
            return None

    return "Done."


def gamelogs_from_url(url):
    return games_from_url(
        'gamelogs', url, 'pgl_basic', 'pgl_basic_playoffs')


def headtoheads_from_url(p1, p2):
    p1_code = find_player_code(p1)
    p2_code = find_player_code(p2)

    payload = {'p1': p1_code, 'p2': p2_code, 'request': 1}
    hth_url = 'http://www.basketball-reference.com/play-index/h2h_finder.cgi'

    return games_from_url(
        'headtoheads', hth_url, 'stats_games', 'stats_games_playoffs',
        p1_code, p2_code, payload)


def add_table_to_db(
        collection_id, table, header, season, url=False,
        p1_code=False, p2_code=False):
    """
    Adds all gamelogs in a table to the database.

    If there is no table returns None, otherwise finds all rows in the table
    and removes the header row. For each row in row, if the collection_id is
    'gamelogs', initialized vals with the player_code, year and season.
    Else, vals is initialized with p1_code, p2_code and season.

    For each column in a row, if collection_id is 'gamelogs', the text is
    appended to vals.
    If the text is a:
        - Date: converts into a datetime object then appends
        - percentage: converts to float then appends
        - number: converts to float then appends
        - string: appends text

        - If empty string, values are added manually based on context.

    A dictionary, gamleog, is created from zipping header and vals. It is then
    inserted into the correct collection based on the collection_id.
    """

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
                elif col_num == (12, 15, 18):
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
                if col_num == (14, 17, 20):
                    vals.append(0.0 if text == '' else float(text))
                elif is_number(text):
                    vals.append(float(text))
                else:
                    vals.append(text)

        gamelog = dict(izip(header, vals))

        with app.app_context():
            db[collection_id].insert(gamelog)
            print db[collection_id].find_one(gamelog)

    return 'done.'


def create_gamelogs_collection():
    """
    Calls gamelogs_from_url for each url in gamelog_urls, which contains all
    seasons for every active player.
    """

    gamelog_urls = open_file('./gamelog_urls')

    for num, url in enumerate(gamelog_urls):
        print (str(((num + 1) * 100) / (len(gamelog_urls))) +
               '%  --  ' +
               url)
        gamelogs_from_url(url)

    return 'ALL GAMELOGS ADDED.'


def create_headtoheads_collection():
    """ Calls headtoheads_from_url for each combination of two active players.
    """

    player_names_urls = open_file('./player_names_urls.json')

    player_names = []
    for name, url in player_names_urls.items():
        player_names.append(name)

    all_hth_dict = []
    player_combinations = list(combinations(player_names, 2))

    for num, c in enumerate(player_combinations):
        print c
        headtoheads_from_url(*c)

    return 'ALL HEADTOHEADS ADDED.'


def create_salaries_collection():
    """
    Adds all player salaries to the database. In the salaries table, each row
    is a player with columns for each year's salary for the duration of the 
    contract.
    """

    salary_url = 'http://www.basketball-reference.com/contracts/players.html'
    table_soup = soup_from_url(salary_url)

    table = table_soup.find(
        'table', attrs={'id': 'contracts'})

    print table





