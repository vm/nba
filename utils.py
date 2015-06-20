import os
from posixpath import basename
from urlparse import urlparse

from app import db


class ConversionsMixin(object):
    @staticmethod
    def date_conversion(text):
        return arrow.get(text).datetime

    @staticmethod
    def home_conversion(text):
        return text != '@'

    @staticmethod
    def winloss_conversion(text):
        return float(_winloss_regex.match(text).group(1))

    @staticmethod
    def percent_conversion(text):
        return None

    @staticmethod
    def plusminus_conversion(text):
        return float(text) if text else 0


def find_player_code(player):
    """Finds a player code given a player name."""
    player_dict = db.players.find_one({'Player': player})
    if not player_dict:
        raise ValueError('Enter a valid player name.')
    return os.path.splitext(basename(urlparse(player_dict['URL']).path))[0]


def find_player_name(player_code):
    """Finds a player name given a player code."""
    return db.players.find_one({"URL": {'$regex': '.*' + player_code + '.*'}})['Player']


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


def multiple_replace(text, adict):
    rx = re.compile('|'.join(map(re.escape, adict)))
    def one_xlat(match):
        return adict[match.group(0)]
    return rx.sub(one_xlat, text)
