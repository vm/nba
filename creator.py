import string
from functools import partial
from itertools import combinations
from multiprocessing import Pool

from app import db
from ingest import GamelogIngester, HeadtoheadIngester, PlayerIngester
from utils import find_player_code

def _get_items(cls, option):
    cls(option).find()


class CollectionCreator(object):
    _pool = Pool(20)

    @classmethod
    def create(cls):
        cls._pool.map(cls._mapped_function, cls._options)


class GamelogsCreator(CollectionCreator):
    _options = (url for player in db.players.find() for url in player['GamelogURLs'])
    _mapped_function = partial(_get_items, cls=GamelogIngester)


class HeadtoheadsCreator(CollectionCreator):
    _options = combinations((find_player_code(player['Player']) for player in db.players.find()), 2)
    _mapped_function = partial(_get_items, cls=HeadtoheadIngester)


class PlayersCreator(CollectionCreator):
    _options = string.ascii_lowercase
    _mapped_function = partial(_get_items, cls=PlayerIngester)

