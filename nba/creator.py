from multiprocessing import Pool

from PyQuery import pyquery as pq

from nba.app import db
from nba.ingest import BasicGamelogIngester, HeadtoheadGamelogIngester

# Multiprocessing forces these functions to be top level.
def gamelogs_from_url(url):
    BasicGamelogIngester(url).find()


def headtoheads_from_combo(combo):
    HeadtoheadGamelogIngester(combo).find()


def players_from_letter(letter):
    PlayerIngester(letter).find()


class CollectionCreator(object):
    _pool = Pool(20)

    def __init__(self, collection, update=True):
        self.collection = collection
        self.update = update

    def find_options(self):
        """Finds a options to add to the database based on the collection."""

        if self.collection == 'players':
            return 'abcdefghijklmnopqrstuvwxyz'
        players = db.players.find()
        if self.collection == 'gamelogs':
            return (url
                    for player in players
                    for url in player['GamelogURLs']
                    if not self.update or '2015' in url)
        else:
            return combinations((find_player_code(player['Player']) for player in players), 2)

    def create(self):
        """Creates a complete collection in the database."""
        if self.collection == 'gamelogs':
            if self.update:
                db.gamelogs.remove({'Year': 2015})
            f = gamelogs_from_url
        elif self.collection == 'headtoheads':
            f = headtoheads_from_combo
        else:
            f = players_from_letter
        CollectionCreator._pool.map(f, self.find_options())

