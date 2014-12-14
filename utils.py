import json
import os
import pickle
import requests
import string

from bs4 import BeautifulSoup
from posixpath import basename
from urlparse import urlparse


def get_header(table):
    """ Returns the header of a table.
    """

    header = []
    try:
        for th in table.findAll('th'):
            col = th.getText()
            col = col.replace('%', 'P') \
                     .replace('3', 'T') \
                     .replace('+/-', 'PlusMinus')

            if col not in header:
                header.append(col)
    except AttributeError:
        return None

    return header


def open_file(path):
    """
    Opens the file at a given path. If the file extension is .json, loads
    JSON. Else, loads pickle.
    """

    with open(path) as f:
        if path.endswith('.json'):
            return json.load(f)
        else:
            return pickle.load(f)


def is_number(s):
    """ Checks if a string is a number.
    """

    try:
        float(s)
        return True
    except ValueError:
        return False


def soup_from_url(url, payload=False):
    """
    Uses BeautifulSoup to scrape a website. Returns the text from the
    requests result. If there is a payload, use it as a GET parameter.
    """

    try:
        if payload is not False:
            r = requests.get(url, params=payload)
        else:
            r = requests.get(url)
        return BeautifulSoup(r.text)
    except:
        return None


def find_player_code(player):
    """ Finds a player code given a player name.
    """
    player_names_urls = open_file('./player_names_urls.json')

    try:
        player_url = player_names_urls[player]
    except KeyError:
        return None

    player_url_path = urlparse(player_url).path
    bn = basename(player_url_path)
    player_code = os.path.splitext(bn)[0]

    return player_code


def path_list_from_url(url):
    """ Splits a url and returns a list of path items.
    """

    o = urlparse(url)
    path_list = o.path.split('/')
    return path_list


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
    Return list of gamelog urls with every year of every current player.

    Open player_names_urls, a JSON file containing a list of dictionaries with
    key values Name and URL. For each dictionary in the list, url is scraped
    and table containing the player totals is stored. Find each single season
    table in the totals table. In each single season table, gamelog url found
    by searching for url column and finding the link
    text.
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
