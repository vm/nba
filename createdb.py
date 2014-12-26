import json
import os
import pickle
import requests
import string

from bs4 import BeautifulSoup
from datetime import datetime
from itertools import combinations, izip
from mongokit import Connection
from posixpath import basename
from urlparse import urlparse

connection = Connection()


class Gamelog(Document):
    __collection__ = 'gamelogs'
    structure = {
        'FT': float,
        'TP': float,
        'TOV': float,
        'Tm': str,
        'GmSc': str,
        'FG': float,
        'TPA': float,
        'DRB': float,
        'Rk': float,
        'Opp': str,
        'AST': float,
        'Season': str,
        'HomeAway': str,
        'Date': datetime,
        'PF': float,
        'WinLoss': float,
        'FGA': float,
        'GS': float,
        'G': float,
        'STL': float,
        'Age': str,
        'TRB': float,
        'FTA': float,
        'BLK': float,
        'PlusMinus': float,
        'PTS': float,
        'Player': str,
        'MP': float,
        'Year': int,
        'ORB': float
    }
    required_fields = ['Opp', 'Season', 'G',  'Age', 'HomeAway', 'Player',
                       'Tm',  'Year',   'Rk', 'GS',  'WinLoss',  'Date']
    use_dot_notation = True


class Headtohead(Document):
    __collection__ = 'headtoheads'
    structure = {
        'Player': str,
        'Opp_Player': str,
        'FT': float,
        'TP': float,
        'TOV': float,
        'Tm': str,
        'FG': float,
        'TPA': float,
        'DRB': float,
        'Rk': float,
        'Opp': str,
        'AST': float,
        'Season': str,
        'HomeAway': str,
        'Date': datetime,
        'PF': float,
        'WinLoss': float,
        'FGA': float,
        'GS': float,
        'STL': float,
        'TRB': float,
        'FTA': float,
        'BLK': float,
        'PTS': float,
        'MP': float,
        'ORB': float
    }
    required_fields = ['Player',  'Opp_Player', 'Opp', 'Season', 'Tm',
                       'WinLoss', 'HomeAway',   'GS',  'Date',   'Rk']
    use_dot_notation = True


class Salary(Document):
    __collection__ = 'salaries'
    structure = {
        'Player': str,
        'Salary': dict
    }
    required_fields = ['Player', 'Salary']
    use_dot_notation = True


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
    'WinLoss', so they are added manually. All percentages are removed.

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
        gamelog_header[8] = 'HomeAway'  # Replaces an empty column title.
        gamelog_header.insert(10, 'WinLoss')  # Inserts a missing column title.

        remove_items = ['FGP', 'FTP', 'TPP']
        for item in sorted(remove_items, reverse=True):
            gamelog_header.remove(item)

        # Adds all gamelogs in regular season table to database.
        add_gamelogs_in_table_to_db(
            collection_id='gamelogs',
            table=reg_table,
            header=gamelog_header,
            season='reg',
            url=url)
        # Adds all gamelogs in playoff table to database.
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
            hth_header = (['player_code_1', 'player_code_2', 'Season'] +
                          hth_header_add)
            hth_header[7] = 'HomeAway'  # Replaces empty column.
            hth_header.insert(9, 'WinLoss')  # Inserts missing column.

            remove_items = ['FGP', 'FTP', 'TPP']
            for item in sorted(remove_items, reverse=True):
                hth_header.remove(item)

            # Adds all gamelogs in regular season table to database.
            add_gamelogs_in_table_to_db(
                collection_id='headtoheads',
                table=reg_table,
                header=hth_header,
                season='reg',
                player_code_1=player_code_1,
                player_code_2=player_code_2)
            # Adds all gamelogs in playoff table to database.
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

    Args:
        gamelog_url (str): basketball-reference url consisting of gamelogs for
            a single year of player stats.

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
    Else, stat_values is initialized with player_code_1, player_code_2 and
    season.

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
        url (str): Basketball-Reference url consisting of gamelogs for a
            single year of player stats.
        player_code_1 (str, optional): Basketball-Reference code for one
            player.
        player_code_2 (str, optional): Basketball-Reference code for another
            player.

    """
    if not table:
        return None

    rows = table.findAll('tr')[1:]
    rows = [r for r in rows if len(r.findAll('td')) > 0]  # Rows except header.

    # Each row is one gamelog.
    for row in rows:
        if collection_id == 'gamelogs':
            path_components = path_components_of_url(url)
            stat_values = [str(path_components[3]),  # Player
                           int(path_components[5]),  # Season
                           season]
        else:
            stat_values = [player_code_1, player_code_2, season]

        # Each column is one stat type.
        for col_num, col in enumerate(row.findAll('td')):
            # print col_num
            text = str(col.getText())
            # print text

            # Stat values are converted by position based on the collection.
            if collection_id == 'gamelogs':
                # Date
                if col_num == 2:
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                # Percentages
                elif col_num == 12 or col_num == 15 or col_num == 18:
                    pass
                # PlusMinus
                elif col_num == 29:
                    stat_values.append(0 if text == '' else float(text))
                # Number
                elif is_number(text):
                    stat_values.append(float(text))
                else:
                    stat_values.append(text)
            if collection_id == 'headtoheads':
                # Date
                if col_num == 2:
                    stat_values.append(datetime.strptime(text, '%Y-%m-%d'))
                # Percentages
                elif col_num == 11 or col_num == 14 or col_num == 17:
                    pass
                # Number
                elif is_number(text):
                    stat_values.append(float(text))
                else:
                    stat_values.append(text)

        # Zips the each header item and stat value together and adds each into
        # a dictionary. This is a dict of gamelog stats for one game with keys
        # for each stat type.
        gamelog = dict(izip(header, stat_values))

        # Instead of player_code_1, player_code_2, Player in headtoheads,
        # removes replaces Player key to player_code_1 if values equal.
        # Otherwise, convert Player to player_code_2 and player_code_1 to
        # Opp_Player.
        if collection_id == 'headtoheads':
            player_code = find_player_code(gamelog['Player'])
            if player_code == gamelog['player_code_1']:
                gamelog.pop('Player', None)
                gamelog['Player'] = gamelog.pop('player_code_1')
                gamelog['Opp_Player'] = gamelog.pop('player_code_2')
            else:
                gamelog.pop('Player', None)
                gamelog['Player'] = gamelog.pop('player_code_2')
                gamelog['Opp_Player'] = gamelog.pop('player_code_1')

        # Initializes connection to the correct collection in database.

        collection = connection[collection_id].users
        collection.insert(gamelog)  # Inserts the gamelog dictionary to db.
        print collection.find_one(gamelog)  # Finds dict to ensure addition.

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

        # Adds gamelogs from a url to the database.
        find_basic_gamelogs_from_url(url)

    return 'ALL GAMELOGS ADDED.'


def create_headtoheads_collection():
    """
    Calls headtoheads_from_url for each combination of two active players.

    """
    with open('./player_names_urls.json') as f:
        player_names_urls = json.load(f)

    player_names = [
        name
        for name, url in player_names_urls.items
    ]

    player_combinations = list(combinations(player_names, 2))
    for num, c in enumerate(player_combinations):
        # Print percentage completion and current combination.
        print (str(((num + 1) * 100) / (len(player_combinations))) +
               '%  --  ' +
               str(c))

        # Adds headtohead gamelogs for a combination the database if the
        # combo exists.
        find_headtohead_gamelogs_from_url(*c)

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


def get_header(table):
    """
    Finds and returns the header of a table.

    Args:
        table: HTML table of gamelog stats for one year. Can be a regular
            season or playoff table, or regular gamelog or headtohead gamelog
            table.

    Returns:
        list of str if table, None otherwise.

    """
    header = []
    try:
        for th in table.findAll('th'):
            col = str(th.getText())
            col = col.replace('%', 'P') \
                     .replace('3', 'T') \
                     .replace('+/-', 'PlusMinus')

            if col not in header:
                header.append(col)
    except AttributeError:
        return None

    return header


def is_number(s):
    """
    Checks if a string is a number.

    Args:
        s (str): a string containing a number.

    Returns:
        bool: True if a string is a number, false otherwise.

    Raises:
        NotImplementedError: If s is not a string.

    """
    if isinstance(s, str):
        try:
            float(s)
            return True
        except ValueError:
            return False
    else:
        raise NotImplementedError('Must enter a string.')


def soup_from_url(url, payload=None):
    """
    Uses BeautifulSoup to scrape a website to get its soup.

    Args:
        url (string): Basketball-Reference url consisting of gamelogs for a
            single year of player stats.
        payload (dict, optional): Payload for a Requests url request. In this
            case, only headtohead_url requires a payload, which contains the
            keys p1, p2 and request.

    Returns:
        BeautifulSoup formatted HTML of scraped url.


    """
    try:
        if payload:
            r = requests.get(url, params=payload)
        else:
            r = requests.get(url)
        return BeautifulSoup(r.text)
    except:
        return None


def find_player_code(player):
    """
    Finds a player code given a player name.

    Args:
        player (str): Name of a player to look up in player_names_urls.

    Returns:
        str: player_code of player if successful.
        None: if player lookup raises KeyError.

    Todo:
        Use MongoDB as a semi-intelligent cache, instatiating players as
            items, inserting and deleting players as needed.

    """
    with open('./player_names_urls.json') as f:
        player_names_urls = json.load(f)

    try:
        player_url = player_names_urls[player]
    except KeyError:
        return None

    player_url_path = urlparse(player_url).path
    bn = basename(player_url_path)
    player_code = os.path.splitext(bn)[0]

    return player_code


def path_components_of_url(url):
    """
    Splits a url and returns a list of components of the url's path.

    """
    o = urlparse(url)
    path_components = o.path.split('/')
    return path_components


def save_player_names_urls():
    """
    Saves a dictionary of player names and basketball-reference home urls.

    Finds the directory of players with last name starting with a specific
    letter for every lowercase letter. Current names have strong tags, so
    finds all current_names.

    """
    names = []
    for letter in string.ascii_lowercase:
        letter_page = soup_from_url(
            'http://www.basketball-reference.com/players/%s/' % (letter))

        current_names = letter_page.findAll('strong')
        for n in current_names:
            name_data = n.children.next()
            names.append(
                (name_data.contents[0],
                 'http://www.basketball-reference.com' +
                 name_data.attrs['href']))

    with open('./player_names_and_urls.json', 'w') as f:
        json.dump(dict(names), f)

    return "PLAYER NAMES AND URLS SAVED."


def save_gamelog_urls():
    """
    Returns list of gamelog urls with every year of every current player.

    Opens player_names_urls, a JSON file containing a list of dictionaries
    with key values Name and URL. For each dictionary in the list, url is
    scraped and the table containing the player totals is stored. Finds each
    single season table in the totals table. In each single season table, the
    gamelog url found by searching for url column and finding the link text.
    """

    player_names_urls = open_player_names_urls()

    gamelog_urls = []
    for name, url in player_names_urls.items():
        table_soup = soup_from_url(url)

        totals_table = table_soup.find('table', attrs={'id': 'totals'})
        all_tables = totals_table.findAll('tr', attrs={'class': 'full_table'})

        for table in all_tables:
            url = table.find('td')
            for link in url.findAll("a"):
                gamelog_urls.append('http://www.basketball-reference.com' +
                                    link.get("href"))

    with open('./gamelog_urls', 'wb') as f:
        pickle.dump(gamelog_urls, f)

    return 'GAMELOG URLS SAVED.'
