import arrow
import numpy
from mongokit import Connection, ObjectId
import datetime
import pickle
from sortedcontainers import SortedListWithKey, SortedList

connection = Connection()


def print_gamelogs(gamelogs):
    if gamelogs:
        for gamelog in gamelogs:
            print gamelog
    else:
        print 'No gamelogs.'
    return


class FindGamelogs(object):
    def __init__(self, query):
        self.query = query
        self.is_gamelog = connection.gamelogs.users.find_one(self.query)
        if self.is_gamelog:
            self.gamelogs = connection.gamelogs.users.find(self.query)

    def all_games(self):
        return [gamelog for gamelog in self.gamelogs]

    def filter_active_games(self):
        if self.is_gamelog:
            return [gamelog for gamelog in self.gamelogs
                    if gamelog['GS'] != 'Inactive'
                       and gamelog['GS'] != 'Did Not Play'
                       and gamelog['GS'] != 'Player Suspended']
        else:
            return None

class CalculateDFSScore(object):
    def __init__(self, gamelogs, site):
        self.gamelogs = gamelogs
        self.site = site

    def is_double_triple_double(self, stats):
        if stats[1] >= 10:
            if stats[2] >= 10:
                return 3.00 # Triple-Double
            else:
                return 1.50 # Double-Double
        else:
            return 0 # Neither

    def create_dfs_scores_sorted_list(self):
        dfs_scores = [dict(score=self.calc_dfs_score_from_gamelog(gamelog),
                           gamelog=gamelog)
                      for gamelog in self.gamelogs]

        return SortedListWithKey(dfs_scores, key=lambda val: -val['score'])

    def print_top_dfs_scores(self, number):
        dfs_scores = self.create_dfs_scores_sorted_list()
        for num, score in enumerate(dfs_scores[0:(number)]):
            print (
                str(num+1) + ') ' +
                str(score['gamelog']['Player']) + ' vs. ' +
                str(score['gamelog']['Opp']) + ' on ' +
                str(score['gamelog']['Date'].strftime("%m/%d/%Y")) + ' -- ' +
                str(score['score']))

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

        elif self.site == 'fanduel':
            FG  = gamelog['FG'] - TP
            FT  = gamelog['FT']
            score = (FG  * 2.00 + TP  * 3.00 + FT  * 1.00 + AST * 1.50 +
                     TRB * 1.20 + STL * 2.00 + BLK * 2.00 - TOV * 1.00)

        else:
            raise NotImplementedError('Only DraftKings and FanDuel scores.')

        return score


class BasicStatOp(object):
    def __init__(self, gamelogs, stat):
        self.gamelogs = gamelogs
        self.stat = stat

    def find_stats(self):
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
    def __init__(self, start, end='now'):
        self.start = start
        self.end = end

    def datetime_range(self):
        start = arrow.get(self.start).datetime.replace(tzinfo=None)
        end = arrow.get(self.end).datetime.replace(tzinfo=None)
        return {'Date': {'$gte': start, '$lt': end}}

if __name__ == '__main__':
    QueryHelpers1 = QueryHelpers('2014-12-20', '2014-12-22')
    my_query = {'Opp': 'WAS'}
    my_query.update(QueryHelpers1.datetime_range())

    games = FindGamelogs(my_query).filter_active_games()
    
    with open('test_sorted_gamelogs', 'wb') as f:
        test_sorted_gamelogs = [
        {'score': 35.75, 'gamelog': {u'PlusMinus': 5.0, u'FT': 5.0, u'TOV': 2.0, u'Tm': u'PHO', u'GmSc': 12.6, u'FG': 6.0, u'DRB': 7.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 3.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 3.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 15.0, u'GS': 1.0, u'TPA': 3.0, u'STL': 1.0, u'Age': u'25-012', u'TRB': 9.0, u'FTA': 6.0, u'BLK': 1.0, u'PTS': 17.0, u'Player': u'bledser01', u'MP': u'28:48', u'Year': 2015, u'_id': ObjectId('54989eb03a4cfc5309df7826'), u'ORB': 2.0}}, {'score': 31.0, 'gamelog': {u'PlusMinus': 0.0, u'FT': 2.0, u'TOV': 3.0, u'Tm': u'PHO', u'GmSc': 12.9, u'FG': 6.0, u'DRB': 5.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 27.0, u'AST': 4.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 2.0, u'PF': 2.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 11.0, u'GS': 1.0, u'TPA': 5.0, u'STL': 1.0, u'Age': u'28-229', u'TRB': 6.0, u'FTA': 2.0, u'BLK': 0.0, u'PTS': 16.0, u'Player': u'dragigo01', u'MP': u'30:48', u'Year': 2015, u'_id': ObjectId('54989fea3a4cfc5309df998e'), u'ORB': 1.0}}, {'score': 26.5, 'gamelog': {u'PlusMinus': 3.0, u'FT': 2.0, u'TOV': 2.0, u'Tm': u'PHO', u'GmSc': 9.0, u'FG': 3.0, u'DRB': 4.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 1.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 5.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 3.0, u'GS': 1.0, u'TPA': 0.0, u'STL': 0.0, u'Age': u'21-188', u'TRB': 8.0, u'FTA': 6.0, u'BLK': 4.0, u'PTS': 8.0, u'Player': u'lenal01', u'MP': u'23:33', u'Year': 2015, u'_id': ObjectId('5498b54f3a4cfc5309e21cea'), u'ORB': 4.0}}, {'score': 20.5, 'gamelog': {u'PlusMinus': 8.0, u'FT': 2.0, u'TOV': 2.0, u'Tm': u'PHO', u'GmSc': 8.5, u'FG': 7.0, u'DRB': 2.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 1.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 1.0, u'PF': 2.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 14.0, u'GS': 1.0, u'TPA': 3.0, u'STL': 0.0, u'Age': u'25-110', u'TRB': 2.0, u'FTA': 2.0, u'BLK': 0.0, u'PTS': 17.0, u'Player': u'morrima02', u'MP': u'35:37', u'Year': 2015, u'_id': ObjectId('5498b54b3a4cfc5309e21c7b'), u'ORB': 0.0}}, {'score': 17.75, 'gamelog': {u'PlusMinus': 9.0, u'FT': 2.0, u'TOV': 1.0, u'Tm': u'PHO', u'GmSc': 5.2, u'FG': 4.0, u'DRB': 2.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 21.0, u'AST': 3.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 1.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 12.0, u'GS': 0.0, u'TPA': 0.0, u'STL': 0.0, u'Age': u'25-317', u'TRB': 3.0, u'FTA': 2.0, u'BLK': 0.0, u'PTS': 10.0, u'Player': u'thomais02', u'MP': u'24:01', u'Year': 2015, u'_id': ObjectId('54989ca03a4cfc5309df3731'), u'ORB': 1.0}}, {'score': 17.5, 'gamelog': {u'PlusMinus': 11.0, u'FT': 1.0, u'TOV': 3.0, u'Tm': u'PHO', u'GmSc': 7.1, u'FG': 5.0, u'DRB': 3.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 0.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 2.0, u'PF': 4.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 7.0, u'GS': 0.0, u'TPA': 3.0, u'STL': 0.0, u'Age': u'28-329', u'TRB': 4.0, u'FTA': 1.0, u'BLK': 0.0, u'PTS': 13.0, u'Player': u'greenge01', u'MP': u'17:43', u'Year': 2015, u'_id': ObjectId('5498b5ec3a4cfc5309e2305b'), u'ORB': 1.0}}, {'score': 17.0, 'gamelog': {u'PlusMinus': 9.0, u'FT': 0.0, u'TOV': 1.0, u'Tm': u'PHO', u'GmSc': 6.6, u'FG': 2.0, u'DRB': 4.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 0.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 2.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 2.0, u'GS': 0.0, u'TPA': 0.0, u'STL': 1.0, u'Age': u'26-111', u'TRB': 6.0, u'FTA': 0.0, u'BLK': 2.0, u'PTS': 4.0, u'Player': u'plumlmi01', u'MP': u'21:27', u'Year': 2015, u'_id': ObjectId('5498ad193a4cfc5309e11c27'), u'ORB': 2.0}}, {'score': 12.5, 'gamelog': {u'PlusMinus': 9.0, u'FT': 0.0, u'TOV': 1.0, u'Tm': u'PHO', u'GmSc': 4.8, u'FG': 5.0, u'DRB': 0.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 29.0, u'AST': 1.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 1.0, u'PF': 2.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 9.0, u'GS': 0.0, u'TPA': 2.0, u'STL': 0.0, u'Age': u'25-110', u'TRB': 0.0, u'FTA': 2.0, u'BLK': 0.0, u'PTS': 11.0, u'Player': u'morrima03', u'MP': u'29:12', u'Year': 2015, u'_id': ObjectId('5498b2f13a4cfc5309e1d560'), u'ORB': 0.0}}, {'score': 11.25, 'gamelog': {u'PlusMinus': 3.0, u'FT': 2.0, u'TOV': 2.0, u'Tm': u'PHO', u'GmSc': 3.8, u'FG': 2.0, u'DRB': 4.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 25.0, u'AST': 0.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 2.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 3.0, u'GS': 1.0, u'TPA': 1.0, u'STL': 0.0, u'Age': u'29-230', u'TRB': 5.0, u'FTA': 2.0, u'BLK': 0.0, u'PTS': 6.0, u'Player': u'tuckepj01', u'MP': u'18:48', u'Year': 2015, u'_id': ObjectId('5498af363a4cfc5309e15a5c'), u'ORB': 1.0}}, {'score': 6.5, 'gamelog': {u'PlusMinus': 3.0, u'FT': 2.0, u'TOV': 0.0, u'Tm': u'PHO', u'GmSc': 1.5, u'FG': 0.0, u'DRB': 2.0, u'Rk': 29.0, u'Opp': u'WAS', u'G': 12.0, u'AST': 0.0, u'Season': u'reg', u'HomeAway': u'@', u'TP': 0.0, u'PF': 1.0, u'Date': datetime.datetime(2014, 12, 21, 0, 0), u'WinLoss': u'W (+12)', u'FGA': 2.0, u'GS': 0.0, u'TPA': 0.0, u'STL': 0.0, u'Age': u'31-027', u'TRB': 2.0, u'FTA': 2.0, u'BLK': 1.0, u'PTS': 2.0, u'Player': u'randosh01', u'MP': u'10:03', u'Year': 2015, u'_id': ObjectId('5498b1883a4cfc5309e1a75c'), u'ORB': 0.0}}]
        pickle.dump(test_sorted_gamelogs, f)


    print CalculateDFSScore(games, 'draftkings').create_dfs_scores_sorted_list()
