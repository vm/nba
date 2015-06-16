from itertools import combinations
from multiprocessing import Pool

from PyQuery import pyquery as pq

from app import db
from ingest import BasicGamelogIngester, HeadtoheadGamelogIngester


def _items_from_option(cls, option):
    cls(option).find()


# Multiprocessing forces these functions to be top level.
def _gamelogs_from_url(url):
    _items_from_option(BasicGamelogIngester, url)


def _headtoheads_from_combo(combo):
    _items_from_option(HeadtoheadGamelogIngester, combo)


def _players_from_letter(letter):
    _items_from_option(PlayerIngester, letter)


class CollectionCreator(object):
    _pool = Pool(20)

    @classmethod
    def create(cls):
        cls._pool.map(cls._mapped_function, cls._options)


class GamelogsCreator(CollectionCreator):
    _options = (url for player in db.players.find() for url in player['GamelogURLs'])
    _mapped_function = _gamelogs_from_url


class HeadtoheadsCreator(CollectionCreator):
    _options = combinations((find_player_code(player['Player']) for player in players), 2)
    _mapped_function = _headtoheads_from_combo


class PlayersCreator(CollectionCreator):
    _options = 'abcdefghijklmnopqrstuvwxyz'
    _mapped_function = _players_from_letter

