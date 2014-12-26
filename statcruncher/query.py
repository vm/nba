import arrow
import numpy
from bson.json_util import dumps
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
        return [
            gamelog[stat]
            for gamelog in self.remove_dnps()
        ]

    def remove_dnps(self):
        return [
            gamelog
            for gamelog in self.gamelogs
            if (
                gamelog['GS'] != 'Inactive'
                and
                gamelog['GS'] != 'Did Not Play'
                and
                gamelog['GS'] != 'Player Suspended'
                )
        ]

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
            for gamelog in self.remove_dnps()
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
            print dumps(score['gamelog'], indent=4)
            print

    def calc_dfs_score_from_gamelog(self, gamelog):
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

            return score

        elif self.site == 'fanduel':
            FG  = gamelog['FG'] - TP
            FT  = gamelog['FT']

            score = (FG  * 2.00 + TP  * 3.00 + FT  * 1.00 + AST * 1.50 +
                     TRB * 1.20 + STL * 2.00 + BLK * 2.00 - TOV * 1.00)

            return score


class QueryHelpers(object):
    def __init__(self, start, end='now'):
        self.start = start
        self.end = end

    def datetime_range(self):
        start = arrow.get(self.start).datetime.replace(tzinfo=None)
        end = arrow.get(self.end).datetime.replace(tzinfo=None)
        return {'Date': {'$gte': start, '$lt': end}}


if __name__ == '__main__':
    my_query = {'Opp': 'WAS'}
    my_query.update(QueryHelpers('2014-12-21', '2014-12-22').datetime_range())
    # print QueryHelpers('2014-12-20', '2014-12-22').datetime_range()
    calculate_dk = Calculate(my_query, "draftkings")
    print calculate_dk.remove_dnps()
    # print calculate_dk.create_dfs_scores_sorted_list()
    # calculate_dk.top_dfs_scores(3)
    # print calculate_dk.find_stats('PTS')

