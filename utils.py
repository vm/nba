import os
import re
from posixpath import basename
from urlparse import urlparse

from app import db


def find_player_code(player):
    """Finds a player code given a player name."""
    player_dict = db.players.find_one({'Player': player})
    if not player_dict:
        raise ValueError('Enter a valid player name.')
    return os.path.splitext(basename(urlparse(player_dict['URL']).path))[0]


def find_player_name(player_code):
    """Finds a player name given a player code."""
    return (db.players
            .find_one({"URL": {'$regex': '.*' + player_code + '.*'}})
            .get('Player'))


def multiple_replace(text, adict):
    def one_xlat(match):
        return adict[match.group(0)]
    rx = re.compile('|'.join(map(re.escape, adict)))
    return rx.sub(one_xlat, text)
