import json
import pickle

from datetime import datetime
from itertools import combinations, izip

from database import connection
from utils import (find_player_code, get_header, is_number,
                   path_components_of_url, soup_from_url)


def find_gamelogs_from_url(
        collection_id,
        url,
        reg_table_id,
        playoff_table_id,
        player_code_1=None,
        player_code_2=None,
        payload=None):
    """
    Adds each gamelog from a given basketball-reference url to the database.

    Scrapes a url and finds tables for regular season and playoff statistics
    and creates a dictionary for each row (each representing one game). The
    dictionaries contain keys for each stat type in the table header.

    The header is initialized with 'Player', 'Year' and 'Season' if
    collection_id is 'gamelogs' or 'p1', 'p2', 'Season' if 'headtoheads' as
    they are not found on the table. This is appended to the header found on
    the table. The header also does not properly contain 'HomeAway' and
    'WinLoss', so they are added manually.

    Args:
        collection_id (str): Name of a collection in the nba database.
        url (str): Basketball-Reference url consisting of gamelogs for a
            single year of player stats.
        reg_table_id (str): Name of the regular season stats table to search
            for in table_soup.
        playoff_table_id (str): Name of the playoff stats table to search for
            in table_soup.
        player_code_1 (str, optional): Basketball-Reference code for one
            player.
        player_code_2 (str, optional): Basketball-Reference code for another
            player.
        payload (dict, optional): Payload for a Requests url request. In this
            case, only headtohead_url requires a payload, which contains the
            keys p1, p2 and request.

    Returns:
        None: If no header if found when the collection_id is 'headtoheads'.
            This means the two players never played each other.

    """
    # Only headtohead_url requires a payload.
    if payload:
        table_soup = soup_from_url(url, payload)
    else:
        table_soup = soup_from_url(url)

    reg_table = table_soup.find('table', attrs={'id': reg_table_id})
    playoff_table = table_soup.find('table', attrs={'id': playoff_table_id})

    # Initializes header based on the collection_id.
    if collection_id == 'gamelogs':
        gamelog_header = (['Player', 'Year', 'Season'] +
                          get_header(reg_table))
        gamelog_header[8] = 'HomeAway' # Replaces an empty column title.
        gamelog_header.insert(10, 'WinLoss') # Inserts a missing column title.

        # Adds all gamelogs in regular season table to database.
        add_gamelogs_in_table_to_db(
            collection_id='gamelogs',
            table=reg_table,
            header=gamelog_header,
            season='reg',
            url=url)
        #Adds all gamelogs in playoff table to database.
        add_gamelogs_in_table_to_db(
            collection_id='gamelogs',
            table=playoff_table,
            header=gamelog_header,
            season='playoff',
            url=url)
    else:
        hth_header_add = get_header(reg_table)

        # Only adds gamelogs to database if a header is found.
        # If no header, that means there are no matchups between the players.
        if hth_header_add:
            hth_header = (['player_name_1', 'player_name_2', 'Season'] +
                          hth_header_add)
            hth_header[7] = 'HomeAway' # Replaces an empty column title.
            hth_header.insert(9, 'WinLoss') # Inserts a missing column title.

            # Adds all gamelogs in regular season table to database.
            add_gamelogs_in_table_to_db(
                collection_id='headtoheads',
                table=reg_table,
                header=hth_header,
                season='reg',
                player_code_1=player_code_1,
                player_code_2=player_code_2)
            #Adds all gamelogs in playoff table to database.
            add_gamelogs_in_table_to_db(
                collection_id='headtoheads',
                table=playoff_table,
                header=hth_header,
                season='playoff',
                player_code_1=player_code_1,
                player_code_2=player_code_2)
        else:
            return None

    return


def find_basic_gamelogs_from_url(gamelog_url):
    """
    Finds all gamelogs from a url to add to the database. This function
    initializes the arguments in find_gamelogs_from_url and calls it as it
    is an abstraction.

    gamelog_url (str): basketball-reference url consisting of gamelogs for a
            single year of player stats.

    """
    return find_gamelogs_from_url(
        collection_id='gamelogs',
        url=gamelog_url,
        reg_table_id='pgl_basic',
        playoff_table_id='pgl_basic_playoffs')


def find_headtohead_gamelogs_from_url(player_name_1, player_name_2):
    """
    Finds all headtohead gamelogs between two players to add to the database.
    Finds the correct url by finding basketball-reference player codes for
    both players and adding it to the general hth_url as a payload.

    This function initializes the arguments in find_gamelogs_from_url and
    calls it as it is an abstraction.

    Args:
        player_code_1 (str): basketball-reference code for one player.
        player_code_2 (str): basketball-reference code for another player.

    """

    player_code_1 = find_player_code(player_name_1)
    player_code_2 = find_player_code(player_name_2)

    payload = {
        'p1': player_code_1,
        'p2': player_code_2,
        'request': 1
    }
    headtohead_url = ('http://www.basketball-reference.com/play-index/' +
                      'h2h_finder.cgi')

    return find_gamelogs_from_url(
        collection_id='headtoheads',
        url=headtohead_url,
        reg_table_id='stats_games',
        playoff_table_id='stats_games_playoffs',
        player_code_1=player_code_1,
        player_code_2=player_code_2,
        payload=payload)


def add_gamelogs_in_table_to_db(
        collection_id,
        table,
        header,
        season,
        url=None,
        player_code_1=None,
        player_code_2=None):
    """
    Adds all gamelogs in a table to the database.

    If there is no table returns None, otherwise finds all rows in the table
    and removes the header row. For each row in row, if the collection_id is
    'gamelogs', initialized stat_values with the player_code, year and season.
    Else, stat_values is initialized with player_code_1, player_code_2 and season.

    For each column in a row, if collection_id is 'gamelogs', the text is
    appended to stat_values, a list of all the stat values.
    
    If the text is a:
        Date: Converts to a datetime object then appends.
        Percentage: Converts to float then appends.
        Number: Converts to float then appends.
        String: Appends text.

        If empty column, base values are added contextually.

    A dictionary is created from zipping header and stat_values. It is then
    inserted into the correct collection based on the collection_id.

    Args:
        collection_id (str): Name of a collection in the nba database.
        table: HTML table of gamelog stats for one year. Can be a regular
            season or playoff table, or regular gamelog or headtohead gamelog
            table.
        header (list of str): Header of the gamelog table, containing strings
            for each column.
        season (str): Season of the gamelog. Either 'reg' or 'playoff'.
        url (str): 
        player_code_1 (str, optional): Basketball-Reference code for one
            player.
        player_code_2 (str, optional): Basketball-Reference code for another
            player.

    """
    if not table:
        return None

    rows = table.findAll('tr')[1:]
    rows = [r for r in rows if len(r.findAll('td')) > 0] # Rows except header.

    # Each row is one gamelog.
    for row in rows:
        if collection_id == 'gamelogs':
            path_components = path_components_of_url(url)
            stat_values = [str(path_components[3]), # Player
                           int(path_components[5]), # Season
                           season]
        else:
            stat_values = [player_code_1, player_code_2, season]

        # Each column is one stat type.
        for col_num, col in enumerate(row.findAll('td')):
            text = str(col.getText())

            # Stat values are converted by position based on the collection.
            if collection_id == 'gamelogs':
                if col_num == 2: # Date
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                elif col_num == (12, 15, 18): # Percentages
                    stat_values.append(0.0 if text == '' else float(text))
                elif col_num == 29: # PlusMinus
                    stat_values.append('0' if text == '' else text)
                elif is_number(text): # Number
                    stat_values.append(float(text))
                else:
                    stat_values.append(text)
            if collection_id == 'headtoheads':
                if col_num == 2: # Date
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                if col_num == (14, 17, 20): # Percentages
                    stat_values.append(0.0 if text == '' else float(text))
                elif is_number(text): # Number
                    stat_values.append(float(text))
                else:
                    stat_values.append(text)

        # Zips the each header item and stat value together and adds each into
        # a dictionary. This is a dict of gamelog stats for one game with keys
        # for each stat type.
        gamelog = dict(izip(header, stat_values))

        # Initializes connection to the correct collection in database.
        collection = connection[collection_id].users
        collection.insert(gamelog) # Inserts the gamelog dictionary to db.
        print collection.find_one(gamelog) # Finds dict to ensure addition.

    return


def create_gamelogs_collection():
    """
    Calls gamelogs_from_url for each url in gamelog_urls, which contains all
    seasons for every active player.

    """
    with open('./gamelog_urls') as f:
        gamelog_urls = pickle.load(f)

    for num, url in enumerate(gamelog_urls):
        # Print percent completion and current url.
        print (str(((num + 1) * 100) / (len(gamelog_urls))) +
               '%  --  ' +
               url)

        gamelogs_from_url(url) # Adds gamelogs from a url to the database.

    return 'ALL GAMELOGS ADDED.'


def create_headtoheads_collection():
    """
    Calls headtoheads_from_url for each combination of two active players.

    """
    with open('./player_names_urls.json') as f:
        player_names_urls = json.load(f)

    player_names = []
    for name, url in player_names_urls.items():
        player_names.append(name)

    player_combinations = list(combinations(player_names, 2))
    for num, c in enumerate(player_combinations):
        # Print percentage completion and current combination.
        print (str(((num + 1) * 100) / (len(player_combinations))) +
               '%  --  ' +
               str(c))

        # Adds headtohead gamelogs for a combination the database if the
        # combo exists.
        headtoheads_from_url(*c)


    return 'ALL HEADTOHEADS ADDED.'


'''
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
'''
