from pymongo import MongoClient

from . import app

connection = MongoClient(app.config['MONGODB_SETTINGS']['host'])


def query_specific_player(player_name):
    """
    Queries for a single player given a string 'FirstName LastName'.
    """

    if player_name:
        return connection.nba.players.find_one(
            {'Player': player_name})
    else:
        raise ValueError('Specify a player name, please!')


def query_games(query, active=False):
    """
    Finds all games in the database from a given query. If active is True,
    filters all games in the database where a player was active. A player
    is considered active if he was not Inactive, Did Not Play
    (Coach's Decision) or Suspended.

    :returns: List of gamelog dicts if is_gamelog, else None
    """

    is_gamelog = connection.nba.gamelogs.find_one(query)

    if is_gamelog:
        gamelogs = connection.nba.gamelogs.find(query)
        if active:
            return gamelogs
        else:
            return [
                gamelog for gamelog in gamelogs
                if gamelog['GS'] not in ['Inactive',
                                         'Did Not Play',
                                         'Player Suspended']
            ]
    else:
        raise ValueError('No gamelogs found based on query.')
