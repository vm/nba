import json
import os
import pickle
import requests
import string

from bs4 import BeautifulSoup
from posixpath import basename
from urlparse import urlparse


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
    if isinstance(s, str) is True:
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

        totals_table = table_soup.find(
            'table', attrs={'id': 'totals'})
        all_tables = totals_table.findAll(
            'tr', attrs={'class': 'full_table'})

        for table in all_tables:
            url = table.find('td')
            for link in url.findAll("a"):
                gamelog_urls.append(
                    'http://www.basketball-reference.com' +
                        link.get("href"))

    with open('./gamelog_urls', 'wb') as f:
        pickle.dump(gamelog_urls, f)

    return 'GAMELOG URLS SAVED.'
