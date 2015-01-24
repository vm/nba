import os

import arrow
from sortedcontainers import SortedListWithKey, SortedList
from pymongo import MongoClient

connection = MongoClient('mongodb://localhost:27017/')


def print_gamelogs(gamelogs):
    """
    Prints each gamelog in a list of gamelogs, a list of dicts, each with
    the stats of a specific player for one game.
    """

    if gamelogs:
        for gamelog in gamelogs:
            print gamelog
    else:
        print 'No gamelogs.'
    return


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
        if self.is_gamelog:
            self.gamelogs = connection.nba.gamelogs.find(self.query)

    def all_games(self):
        """
        Finds all games in the database from a given query and returns
        list of gamelog dicts.
        """

        return [gamelog for gamelog in self.gamelogs]

    def filter_active_games(self):
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


class CalculateDFSScore(object):
    """DFS score from gamelogs.
    """

    def __init__(self, gamelogs, site):
        """
        Initialized with the list of gamelogs used to calculate scores from
        and the DFS site, which can be 'draftkings' or 'fanduel'.
        """

        self.gamelogs = gamelogs
        self.site = site

    def is_double_triple_double(self, stats):
        """
        Checks if a game was a double-double or triple-double by checking
        number of stat types over 10 in stats, a SortedList of floats ordered
        backwards.
        """

        # SortedList is ordered backwards, so only need to check second and
        # third items.
        if stats[1] >= 10:
            if stats[2] >= 10:
                return 3.00 # Triple-Double
            else:
                return 1.50 # Double-Double
        else:
            return 0 # Neither

    def create_dfs_scores_sorted_list(self):
        """
        Sorts gamelogs by DFS score. A dict for each gamelog is created, 
        with the gamelog itself and its associated DFS score
        (based on the site). Returns a SortedListWithKey of gamelogs sorted by
        DFS score in reverse order.
        """

        dfs_scores = [
            dict(score=self.calc_dfs_score_from_gamelog(gamelog),
                 gamelog=gamelog)
            for gamelog in self.gamelogs
        ]

        return SortedListWithKey(dfs_scores, key=lambda val: -val['score'])

    def print_top_dfs_scores(self, number):
        """Prints the top inputted number of DFS scores in the given gamelogs. 
        """

        dfs_scores = self.create_dfs_scores_sorted_list()

        for num, score in enumerate(dfs_scores[0:(number)]):
            print (
                str(num+1) + ') ' +
                str(score['gamelog']['Player']) + ' vs. ' +
                str(score['gamelog']['Opp']) + ' on ' +
                str(score['gamelog']['Date'].strftime("%m/%d/%Y")) + ' -- ' +
                str(score['score']))

    def calc_dfs_score_from_gamelog(self, gamelog):
        """
        Calculates the DFS score for a given gamelog, a dict with the stats
        of a player for one game. Based on self.class, the a DFS score is
        calculated and returned. Raises a NotImplementedError if site is not
        'fanduel' or 'draftkings'.
        """

        TP  = gamelog['TP']
        AST = gamelog['AST']
        TRB = gamelog['TRB']
        STL = gamelog['STL']
        BLK = gamelog['BLK']
        TOV = gamelog['TOV']

        if self.site == 'draftkings':
            PTS = gamelog['PTS']

            sorted_stats = SortedListWithKey(
                [PTS, AST, TRB, STL, BLK],
                key=lambda val: -val)

            DDorTD = self.is_double_triple_double(sorted_stats)
            score = (PTS * 1.00 + TP  * 0.50 + AST * 1.50 + TRB * 1.25 +
                     STL * 2.00 + BLK * 2.00 - TOV * 0.50 + DDorTD)

        elif self.site == 'fanduel':
            FG  = gamelog['FG'] - TP
            FT  = gamelog['FT']

            score = (FG  * 2.00 + TP  * 3.00 + FT  * 1.00 + AST * 1.50 +
                     TRB * 1.20 + STL * 2.00 + BLK * 2.00 - TOV * 1.00)

        else:
            raise NotImplementedError('Only DraftKings and FanDuel scores.')

        return score


class BasicStatOp(object):
    """Basic operations for statistics.
    """

    def __init__(self, gamelogs, stat):
        """
        Initialized with gamelogs, a list of dicts, each with the stats of
        a specific player for one game, and a stat type to operate on, which
        must be found in a gamelog.
        """

        self.gamelogs = gamelogs
        self.stat = stat

    def find_stats(self):
        """
        Finds all the stats for a specific stat type in self.gamelogs.
        Returns a list of float of specific stat.
        """

        if self.gamelogs:
            return [gamelog[self.stat] for gamelog in self.gamelogs]
        else:
            return None

    def stat_avg(self):
        """Finds the average of specific stat in self.gamelogs.
        """

        stats = self.find_stats()
        if stats:
            return sum(stats) / float(len(stats))
        else:
            return None


class QueryHelpers(object):
    """Query helpers for querying the database.
    """

    def __init__(self, start, end='now'):
        """
        Initialized with start and end of the date range in MM/DD/YY format.
        End defaults to 'now' if no end entered.
        """

        self.start = start
        self.end = end

    def datetime_range(self):
        """
        Returns a dict with one key Date with a start and end time, which can
        be used in a query for gamelogs in a specific date range.
        """

        start = arrow.get(self.start).datetime.replace(tzinfo=None)
        end = arrow.get(self.end).datetime.replace(tzinfo=None)

        return {'Date': {'$gte': start, '$lt': end}}

