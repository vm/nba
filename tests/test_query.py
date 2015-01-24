import datetime
import pickle

import pytest
from mongokit import ObjectId
from sortedcontainers import SortedListWithKey

from nba.query import *

with open('test_files/test_dfs_gamelogs') as f:
    test_dfs_gamelogs = pickle.load(f)
with open('test_files/test_gamelogs') as f:
    test_gamelogs = pickle.load(f)
with open('test_files/test_active_games_list') as f:
    test_active_games_list = pickle.load(f)
with open('test_files/test_sorted_gamelogs') as f:
    test_sorted_gamelogs = pickle.load(f)


def test_print_gamelogs(capsys):
    print_gamelogs(test_gamelogs)
    out, err = capsys.readouterr()
    expected = open('test_files/print_gamelogs.out', 'r').read()
    assert out == expected


def test_print_gamelogs_none(capsys):
    print_gamelogs([])
    out, err = capsys.readouterr()
    assert out == 'No gamelogs.\n'


class TestCalculateDFSScore(object):
    @classmethod
    def setup_class(self):
        self.c_dk = CalculateDFSScore(test_dfs_gamelogs, 'draftkings')
        self.c_fd = CalculateDFSScore(test_dfs_gamelogs, 'fanduel')
        self.c_vt = CalculateDFSScore(test_dfs_gamelogs, 'victiv')
        self.q = QueryHelpers('2014-12-20', '2014-12-22')
        self.my_query = {'Opp': 'WAS'}
        self.my_query.update(self.q.datetime_range())
        self.g = QueryGamelogs(self.my_query)
        self.test_dfs_gamelog = {
            'PlusMinus': 19.0,
            'FT': 10.0,
            'TOV': 2.0,
            'Tm': 'POR',
            'GmSc': 38.8,
            'FG': 11.0,
            'DRB': 5.0,
            'Rk': 30.0,
            'Opp': 'OKC',
            'G': 30.0,
            'AST': 11.0,
            'Season': 'reg',
            'HomeAway': '@',
            'TP': 8.0,
            'PF': 1.0,
            'Date': datetime.datetime(2014, 12, 23, 0, 0),
            'WinLoss': 'W (+4)',
            'FGA': 21.0,
            'GS': 1.0,
            'TPA': 12.0,
            'STL': 2.0,
            'Age': '24-161',
            'TRB': 6.0,
            'FTA': 11.0,
            'BLK': 0.0,
            'PTS': 40.0,
            'Player': 'lillada01',
            'MP': '45:46',
            'Year': '2015',
            'ORB': 1.0}

    def test_calc_dfs_score_from_gamelog_draftkings(self):
        assert self.c_dk.calc_dfs_score_from_gamelog(
            self.test_dfs_gamelog) == 72.5

    def test_calc_dfs_score_from_gamelog_fanduel(self):
        assert self.c_fd.calc_dfs_score_from_gamelog(
            self.test_dfs_gamelog) == 65.7

    def test_calc_dfs_score_from_gamelog_not_implemented(self):
        with pytest.raises(NotImplementedError):
            self.c_vt.calc_dfs_score_from_gamelog(self.test_dfs_gamelog)

    def test_is_double_double(self):
        assert self.c_dk.is_double_triple_double(
            [10, 10, 10, 5, 3, 2]) == 3.00

    def test_is_triple_double(self):
        assert self.c_dk.is_double_triple_double([12, 11, 4, 3, 2]) == 1.50

    def test_is_not_double_or_triple_double(self):
        assert self.c_dk.is_double_triple_double([9, 8, 4, 3]) == 0


class TestBasicStatOp(object):
    @classmethod
    def setup_class(self):
        self.b = BasicStatOp(test_gamelogs, 'PTS')
        self.b_empty = BasicStatOp([], 'PTS')

    def test_find_stats(self):
        assert self.b.find_stats() == [31.0, 12.0, 23.0]

    def test_find_stats_none(self):
        assert self.b_empty.find_stats() is None

    def test_stat_avg(self):
        assert self.b.stat_avg() == 22.0

    def test_stat_avg_none(self):
        assert self.b_empty.stat_avg() is None


class TestQueryHelpers(object):
    @classmethod
    def setup_class(self):
        self.q = QueryHelpers('2014-12-20', '2014-12-22')

    def test_create_datetime_range(self):
        assert self.q.datetime_range() == {
            'Date': {
                '$gte': datetime.datetime(2014, 12, 20, 0, 0),
                '$lt': datetime.datetime(2014, 12, 22, 0, 0)
            }}
