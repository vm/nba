from __future__ import absolute_import

import os
import sys
from datetime import datetime
from posixpath import basename
if sys.version_info > (3, 0):
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

from .app import db


def find_player_code(player):
    """
    Finds a player code given a player name.

    :returns: Player_code of player if successful.
    :raises: ValueError if invalid player name.
    """

    player_dict = db.players.find_one({'Player': player})
    if not player_dict:
        raise ValueError('Enter a valid player name.')

    bn = basename(urlparse(player_dict['URL']).path)
    return os.path.splitext(bn)[0]


def find_player_name(player_code):
    """
    Finds a player name given a player code
    """

    query = {"URL": {'$regex': '.*' + player_code + '.*'}}
    player_dict = db.players.find_one(query)
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
        raise TypeError('Must enter a string.')


def datetime_range(start, end=None):
    """
    Returns a dict with one key Date with a start and end time, which can be used in a query for
    gamelogs in a specific date range.

    :param start: Start date in 'YYYY/MM/DD' format.
    :param end: (optional) End date in 'YYYY/MM/DD' format.
    :returns: Dictionary with a datetime range.
    """

    start_range = datetime.strptime(start, '%Y-%m-%d')
    end_range = datetime.strptime(end, '%Y-%m-%d') if end else datetime.now()
    return {'Date': {'$gte': start_range, '$lt': end_range}}
