from __future__ import absolute_import

from .app import db


def query_specific_player(player_name):
    """
    Queries for a single player.

    :param player_name: 'FirstName LastName'
    :returns: Player dictionary of info.
    :raises: ValueError if no player found.
    """

    if player_name:
        return db.players.find_one({'Player': player_name})
    else:
        raise ValueError('Specify a player name, please!')


def query_games(query, active=False):
    """
    Finds all games in the database from a given query. If active is True, filters all games in the
    database where a player was active. A player is considered active if he was not Inactive, Did
    Not Play (Coach's Decision) or Suspended.

    :param query:
    :param active: Filters active games if True, default False.
    :returns: List of gamelog dicts if is_gamelog, else None.
    :raises: ValueError if no gamelogs found.
    """

    is_gamelog = db.gamelogs.find_one(query)
    if is_gamelog:
        gamelogs = db.gamelogs.find(query)
        if active:
            return gamelogs
        else:
            return [gamelog
                    for gamelog in gamelogs
                    if gamelog['GS'] not in {'Inactive', 'Did Not Play', 'Player Suspended'}]
    else:
        raise ValueError('No gamelogs found based on query.')
