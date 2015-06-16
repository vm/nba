import os
from posixpath import basename
from urlparse import urlparse

from app import db


def find_player_code(player):
    """Finds a player code given a player name."""
    player_dict = db.players.find_one({'Player': player})
    if not player_dict:
        raise ValueError('Enter a valid player name.')
    bn = basename(urlparse(player_dict['URL']).path)
    return os.path.splitext(bn)[0]


def find_player_name(player_code):
    """Finds a player name given a player code."""
    query = {"URL": {'$regex': '.*' + player_code + '.*'}}
    player_dict = db.players.find_one(query)
    return player_dict['Player']


def is_number(s):
    """Checks if a string is a number."""
    if isinstance(s, str):
        try:
            float(s)
            return True
        except ValueError:
            return False
    else:
        raise TypeError('Must enter a string.')

