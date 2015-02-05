import asyncio
import os
from collections import OrderedDict
from datetime import datetime
from posixpath import basename
from urllib.parse import urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

from .app import db


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

    :returns: Player_code of player if successful.
    :raises: ValueError if invalid player name.
    """
    player_dict = db.players.find_one(dict(Player=player))
    if not player_dict:
        raise ValueError('Enter a valid player name.')

    player_url = player_dict['URL']
    player_url_path = urlparse(player_url).path
    bn = basename(player_url_path)
    player_code = os.path.splitext(bn)[0]

    return player_code


def find_player_name(player_code):
    """
    Finds a player name given a player code
    """
    player_dict = db.players.find_one(
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


def path_components_of_url(url):
    """
    Splits a url and returns a list of components of the url's path.
    """
    o = urlparse(url)
    path_components = o.path.split('/')
    return path_components


def datetime_range(start, end=None):
    """
    Returns a dict with one key Date with a start and end time, which can
    be used in a query for gamelogs in a specific date range.
    """
    start_dt = datetime.strptime(start, '%Y-%m-%d')
    end_dt = datetime.strptime(end, '%Y-%m-%d') if end else datetime.now()
    return {'Date': {'$gte': start_dt, '$lt': end_dt}}
