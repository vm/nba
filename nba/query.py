import arrow
from pymongo import MongoClient

connection = MongoClient('mongodb://localhost:27017/')


class QueryPlayers(object):
    """Queries some players. This will probably go away at some point.
    """
    def query_specific_player(self, player_name=None):
        """Queries for a single player given a string 'FirstName LastName'.
        """

        if player_name:
            return connection.nba.players.find_one({'Player': player_name})
        else:
            raise ValueError('Specify a player name, please!')


class QueryGamelogs(object):
    """Gamelogs based on a given query.
    """
    def __init__(self, query):
        """
        Initialized with a MongoDB query, which is a dict such as
        {'PTS': 30, 'Player': 'Kobe Bryant'}

        """
        self.query = query
        self.is_gamelog = connection.nba.gamelogs.find_one(self.query)
        if self.is_gamelog:  # Only need to get all gamelogs if any exist.
            self.gamelogs = connection.nba.gamelogs.find(self.query)

    def all_games(self):
        """
        Finds all games in the database from a given query and returns
        list of gamelog dicts.

        """
        return [gamelog for gamelog in self.gamelogs]

    def active_games(self):
        """
        Filters all games in the database where a player was active. A player
        is considered active if he was not Inactive, Did Not Play
        (Coach's Decision) or Suspended. Returns list of gamelog dicts if
        self.is_gamelog, else None.

        """
        if self.is_gamelog:
            return [
                gamelog for gamelog in self.gamelogs
                if gamelog['GS'] != 'Inactive'
                   and gamelog['GS'] != 'Did Not Play'
                   and gamelog['GS'] != 'Player Suspended'
            ]
        else:
            return None


def datetime_range(start, end=None):
    """
    Returns a dict with one key Date with a start and end time, which can
    be used in a query for gamelogs in a specific date range.

    """
    start_dt = arrow.get(start).datetime.replace(tzinfo=None)
    if end:
        end_dt = arrow.get(end).datetime.replace(tzinfo=None)
    else:
        end_dt = arrow.now().datetime

    return {'Date': {'$gte': start_dt, '$lt': end_dt}}
