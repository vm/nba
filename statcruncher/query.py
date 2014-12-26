import arrow
import bson.json_util
import numpy
from mongokit import Connection
from sortedcontainers import SortedListWithKey, SortedList

import createdb


connection = Connection()

class Calculate(object):
    """
    example queries:
        my_query = {'PTS': {'$gt': 30}}
        my_query = dict(PTS=81)
        my_query = QueryHelpers(-100).datetime_range()

    calculate = Calculate(my_query)

    calculate.top_dfs_scores(15)
    calculate.print_gamelogs()
    calculate.find_stats('PTS')

    """

    def __init__(self, query, site):
        self.query = query
        self.site = site
        self.gamelogs = connection.gamelogs.users.find(self.query)

    def print_gamelogs(self):
        for gamelog in self.gamelogs:
            print gamelog
        return

    def find_stats(self, stat):
        if connection.gamelogs.users.find_one(self.query):
            return [
                gamelog[stat]
                for gamelog in self.remove_dnps(self.gamelogs)
            ]
        else:
            return None

    def remove_dnps(self, gamelogs):
        if gamelogs:
            return [
                gamelog
                for gamelog in gamelogs
                if (gamelog['GS'] != 'Inactive'
                    and
                    gamelog['GS'] != 'Did Not Play'
                    and
                    gamelog['GS'] != 'Player Suspended')
            ]
        else:
            return None

    def stat_avg(self, stat):
        stats = self.find_stats(stat)
        if stats:
            return numpy.mean(self.find_stats(stat))
        else:
            return None

    def is_double_triple_double(self, stats):
        if stats[1] >= 10:
            if stats[2] >= 10:
                return 3.00 # Triple Double
            else:
                return 1.50 # Double Double
        else:
            return 0 # Neither

    def create_dfs_scores_sorted_list(self):
        dfs_scores = [
            dict(score=self.calc_dfs_score_from_gamelog(gamelog),
                 gamelog=gamelog)
            for gamelog in self.remove_dnps(self.gamelogs)
        ]

        return SortedListWithKey(dfs_scores, key=lambda val: -val['score'])

    def top_dfs_scores(self, number):
        dfs_scores = self.create_dfs_scores_sorted_list()
        for num, score in enumerate(dfs_scores[0:(number)]):
            print (
                str(num+1) +
                ') ' +
                str(score['gamelog']['Player']) +
                ' vs. ' +
                str(score['gamelog']['Opp']) +
                ' on ' +
                str(score['gamelog']['Date'].strftime("%m/%d/%Y")) +
                ' -- ' +
                str(score['score']))
            print bson.json_util.dumps(score['gamelog'], indent=4)
            print

    def calc_dfs_score_from_gamelog(self, gamelog):
        TP  = gamelog['TP']
        AST = gamelog['AST']
        TRB = gamelog['TRB']
        STL = gamelog['STL']
        BLK = gamelog['BLK']
        TOV = gamelog['TOV']

        if self.site == 'DraftKings':
            PTS = gamelog['PTS']

            sorted_stats = SortedListWithKey(
                list(PTS, AST, TRB, STL, BLK),
                key=lambda val: -val)
            DDorTD = self.check_double_triple_double(sorted_stats)

            score = (PTS * 1.00 + TP  * 0.50 + AST * 1.50 + TRB * 1.25 +
                     STL * 2.00 + BLK * 2.00 - TOV * 0.50 + DDorTD)

        elif self.site == 'Fanduel':
            FG  = gamelog['FG'] - TP
            FT  = gamelog['FT']

            score = (FG  * 2.00 + TP  * 3.00 + FT  * 1.00 + AST * 1.50 +
                     TRB * 1.20 + STL * 2.00 + BLK * 2.00 - TOV * 1.00)

        return score


class QueryHelpers(object):
    def __init__(self, start=None, end=None):
        self.days_range = days_range

    def datetime_range(self):
        start = arrow.utcnow().replace(days=self.days_range).datetime
        end = arrow.utcnow().datetime
        return {'Date': {'$gte': start, '$lt': end}}


if __name__ == '__main__':
    my_query = QueryHelpers(-365).datetime_range()
    calculate1 = Calculate(my_query, "DraftKings")
    calculate1.top_dfs_scores(5)
