import os
from collections import OrderedDict
from posixpath import basename
from urlparse import urlparse

import arrow
import requests
from bs4 import BeautifulSoup
from mongokit import Connection
from pymongo import MongoClient

from . import app

connection = MongoClient(app.config['MONGODB_SETTINGS']['host'])


def get_header(table):
    """
    Finds and returns the header of a table.
    """
    try:
        header = [
            get_column_title(str(th.getText()))  # Gets header text.
            for th in table.findAll('th')  # Finds all header titles.
        ]
        return list(OrderedDict.fromkeys(header))  # Removes duplicate items.
    except AttributeError:
        return None


def get_column_title(th):
    """
    Gets the header row of a single column. Used in get_header function.
    """
    return th.replace('%','P').replace('3','T').replace('+/-','PlusMinus')


def find_player_code(player):
    """
    Finds a player code given a player name.

    :returns: Player_code of player if successful, None if player lookup
        raises KeyError.
    """
    player_dict = connection.nba.players.find_one(dict(Player=player))
    player_url = player_dict['URL']

    player_url_path = urlparse(player_url).path
    bn = basename(player_url_path)
    player_code = os.path.splitext(bn)[0]

    return player_code


def find_player_name(player_code):
    """
    Finds a player name given a player code
    """
    player_dict = connection.nba.players.find_one(
        {"URL": {'$regex': '.*' + player_code + '.*'}})

    return player_dict['Player']


def is_number(s):
    """
    Checks if a string is a number.

    :returns: True or False
    :raises: NotImplementedError if not inputted string.
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
    Uses BeautifulSoup to scrape a website and returns parsed HTML.

    :param url: Basketball-Reference url of gamelogs for a single year of
        player stats.
    :param payload: Payload for a Requests url request, in this case only
        headtohead_url requires a payload containing the keys p1, p2 and
        request. Defaults to None.
    :returns: BeautifulSoup parsed HTML.
    """
    try:
        if payload:
            r = requests.get(url, params=payload)
        else:
            r = requests.get(url)
        return BeautifulSoup(r.text)
    except:
        return None


def path_components_of_url(url):
    """
    Splits a url and returns a list of components of the url's path.
    """
    o = urlparse(url)
    path_components = o.path.split('/')
    return path_components


def get_gamelog_urls(player_url):
    """
    Returns list of gamelog urls with every year for one player.
    """
    table_soup = soup_from_url(player_url)

    # Table containing player totals.
    totals_table = table_soup.find('table', attrs={'id': 'totals'})
    # All single season tables.
    all_tables = totals_table.findAll('tr', attrs={'class': 'full_table'})

    return [
        'http://www.basketball-reference.com' + link.get("href")
        for table in all_tables
        for link in table.find('td').findAll("a")
    ]


def datetime_range(start, end=None):
    """
    Returns a dict with one key Date with a start and end time, which can
    be used in a query for gamelogs in a specific date range.
    """
    start_dt = arrow.get(start).datetime.replace(tzinfo=None)
    if end:
        end_dt = arrow.get(end).datetime.replace(tzinfo=None)
    else:
        end_dt = arrow.now().datetime

    return {'Date': {'$gte': start_dt, '$lt': end_dt}}
