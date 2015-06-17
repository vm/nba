from itertools import combinations
from multiprocessing import Pool

from pyquery import PyQuery as pq

from app import db
from ingest import GamelogIngester, HeadtoheadIngester
from utils import find_player_code

def _get_items(cls, option):
    cls(option).find()


# Multiprocessing forces these functions to be top level.
def _get_gamelogs(url):
    _get_items(GamelogIngester, url)


def _get_headtoheads(combo):
    _get_items(HeadtoheadIngester, combo)


def _get_players(letter):
    _get_items(PlayerIngester, letter)


class CollectionCreator(object):
    _pool = Pool(20)

    @classmethod
    def create(cls):
        cls._pool.map(cls._mapped_function, cls._options)


class GamelogsCreator(CollectionCreator):
    _options = (url for player in db.players.find() for url in player['GamelogURLs'])
    _mapped_function = _gamelogs_from_url


class HeadtoheadsCreator(CollectionCreator):
    _options = combinations((find_player_code(player['Player']) for player in db.players.find()), 2)
    _mapped_function = _headtoheads_from_combo


class PlayersCreator(CollectionCreator):
    _options = 'abcdefghijklmnopqrstuvwxyz'
    _mapped_function = _players_from_letter

