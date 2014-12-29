import arrow
import numpy
from mongokit import Connection
from sortedcontainers import SortedListWithKey, SortedList

connection = Connection()


def print_gamelogs(gamelogs):
    """
    Prints each gamelog in a list of gamelogs.

    Args:
        gamelogs (list of dict): A list of dicts, each with the stats of a
            specific player for one game.

    """
    if gamelogs:
        for gamelog in gamelogs:
            print gamelog
    else:
        print 'No gamelogs.'
    return


class FindGamelogs(object):
    """
    Gamelogs based on a given query.

    """
    def __init__(self, query):
        """
        Args:
            query (dict): Used to query the MongoDB database.

        Examples:
            >>> FindGamelogs(dict(Player='curryst01', PTS={'$gt': 30}))
            >>> FindGamelogs({'PTS': 81})

        """
        self.query = query
        self.is_gamelog = connection.gamelogs.users.find_one(self.query)
        if self.is_gamelog:
            self.gamelogs = connection.gamelogs.users.find(self.query)

    def all_games(self):
        """
        Finds all games in the database from a given query.

        Returns:
            list of dict: A list of gamelogs.

        """
        return [gamelog for gamelog in self.gamelogs]

    def filter_active_games(self):
        """
        Filters all games in the database where a player was active.

        A player is considered active if he was not Inactive, Did Not Play
        (Coach's Decision) or Suspended.

        Returns:
            list of dict, each being a gamelog, if self.is_gamelog, else None.

        """
        if self.is_gamelog:
            return [gamelog for gamelog in self.gamelogs
                    if gamelog['GS'] != 'Inactive'
                       and gamelog['GS'] != 'Did Not Play'
                       and gamelog['GS'] != 'Player Suspended']
        else:
            return None


class CalculateDFSScore(object):
    """
    Used to calculate DFS scores from gamelogs.

    """
    def __init__(self, gamelogs, site):
        """
        Args:
            gamelogs (list of dict): The list of gamelogs used to calculate
                scores from.
            site (str): DFS site. Can be 'draftkings' or 'fanduel'.

        Examples:
            >>> c = CalculateDFSScore(
            ...     FindGamelogs(dict(Player='curryst01', PTS={'$gt': 30})),
            ...                  'draftkings')

        """
        self.gamelogs = gamelogs
        self.site = site

    def is_double_triple_double(self, stats):
        """
        Checks if a game was a double-double or triple-double by checking the
        number of stat types with over 10.

        A SortedList is checked to see how many items are over 10, and a
        value is returned based on that.

        Args:
            stats (SortedList of float): each being one stat type such as PTS.

        Return:
            float: 3.00 if triple-double, 1.50 if double-double
            int: 0 if neither.

        """
        if stats[1] >= 10:
            if stats[2] >= 10:
                return 3.00 # Triple-Double
            else:
                return 1.50 # Double-Double
        else:
            return 0 # Neither

    def create_dfs_scores_sorted_list(self):
        """
        Sorts gamelogs by DFS score.

        A dict for each gamelog is created, with the gamelog itself and its 
        associated DFS score (based on the site). They are sorted in reverse
        order by scores, with the highest scoring gamelog at the start.

        Returns:
            SortedListWithKey: Sorted list of gamelogs by DFS score.

        """
        dfs_scores = [dict(score=self.calc_dfs_score_from_gamelog(gamelog),
                           gamelog=gamelog)
                      for gamelog in self.gamelogs]

        return SortedListWithKey(dfs_scores, key=lambda val: -val['score'])

    def print_top_dfs_scores(self, number):
        """
        Prints the top DFS scores in the given gamelogs.

        Examples:
            >>> c.print_top_dfs_scores(3)

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
        Calculates the DFS score for a given gamelog. Based on self.class,
        the score is calculated.

        Args:
            gamelog (dict): A dict with the stats of a specific player for one
                game.

        Returns:
            score (float): DFS score of a gamelog.

        Raises:
            NotImplementedError: If site is not fanduel or draftkings.

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
    """
    Basic operations for statistics.

    """
    def __init__(self, gamelogs, stat):
        """
        Args:
            gamelogs (list of dict): A list of dicts, each with the stats of a
                specific player for one game.
            stat (str): Stat type to operate on, must be found in a gamelog.

        Examples:
            >>> b = BasicStatOp(
            ...     FindGamelogs(dict(Player='curryst01',
            ...                  PTS={'$gt': 30}))), 'PTS')

        """
        self.gamelogs = gamelogs
        self.stat = stat

    def find_stats(self):
        """
        Finds all the stats for a specific stat type in self.gamelogs.

        Returns:
            list of float: List of stats of specific stat.
        """
        if self.gamelogs:
            return [gamelog[self.stat] for gamelog in self.gamelogs]
        else:
            return None

    def stat_avg(self):
        stats = self.find_stats()
        if stats:
            return numpy.mean(stats)
        else:
            return None


class QueryHelpers(object):
    """
    Query helpers for querying the database.

    """
    def __init__(self, start, end='now'):
        """
        Args:
            start (str): The start of the time range.
            end (str, optional): The end of the time range. Initialized with
                'now' if no end entered.

        Example:
            >>> q = QueryHelpers('1/2/13', '2/2/13')

        """
        self.start = start
        self.end = end

    def datetime_range(self):
        """
        Creates a dict with one key 'Date' with a start and end time, which
        can be used to query the database for gamelogs in a specific time
        rangle. The dict can either be used as the entire query or added onto
        other parameters.

        Returns:
            dict: The Date parameter for a query.

        """
        start = arrow.get(self.start).datetime.replace(tzinfo=None)
        end = arrow.get(self.end).datetime.replace(tzinfo=None)

        return {'Date': {'$gte': start, '$lt': end}}
