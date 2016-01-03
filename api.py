import string
from functools import partial
from itertools import combinations
from multiprocessing import Pool

from tqdm import tqdm

from app import db
from ingest import GamelogIngester, HeadtoheadIngester, PlayerIngester
from utils import find_player_code


def _get_items(ingester, option):
    """Call find on a given class."""
    ingester(option).find()


def create(collection):
    """Create a collection in the nba database."""
    if collection == 'gamelogs':
        options = (
            url
            for player in db.players.find()
            for url in player['GamelogURLs']
        )
        ingester = GamelogIngester
    elif collection == 'headtoheads':
        options = combinations((find_player_code(player['Player'])
                                for player in db.players.find()), 2)
        ingester = HeadtoheadIngester
    elif collection == 'players':
        options = string.ascii_lowercase
        ingester = PlayerIngester
    else:
        raise NotImplementedError('Not a supported collection type.')
    for option in tqdm(options):
        _get_items(ingester, option)

