import pytest

import createdb
from query import Calculate, QueryHelpers

class TestCreatedb(object):
    def test_is_number_true(self):
        assert createdb.is_number('5') is True

    def test_is_number_false(self):
        assert createdb.is_number('MIA') is False

    def test_is_number_string(self):
        with pytest.raises(NotImplementedError):
            createdb.is_number(56)

    def test_path_components_from_url(self):
        path_components = ['', 'players', 'd', 'duranke01', 'gamelog',
                           '2014', '']
        assert createdb.path_components_of_url(
            'http://www.basketball-reference.com/players/d/duranke01/' +
                'gamelog/2014/') == path_components

    def test_get_gamelog_header(self):
        gamelog_soup = createdb.soup_from_url(
            'http://www.basketball-reference.com/players/d/duranke01/' +
                'gamelog/2015/')

        reg_table = gamelog_soup.find('table', attrs={'id': 'pgl_basic'})

        assert createdb.get_header(reg_table) == \
            [u'Rk',  u'G',   u'Date', u'Age',  u'Tm',  u'',    u'Opp', u'GS',
             u'MP',  u'FG',  u'FGA',  u'FGP',  u'TP',  u'TPA', u'TPP', u'FT',
             u'FTA', u'FTP', u'ORB',  u'DRB',  u'TRB', u'AST', u'STL', u'BLK',
             u'TOV', u'PF',  u'PTS',  u'GmSc', u'PlusMinus']

    def test_get_hth_header(self):
        hth_soup = createdb.soup_from_url(
            'http://www.basketball-reference.com/play-index/h2h_finder.cgi?' +
                'request=1&p1=jamesle01&p2=duranke01#stats_playoffs')

        reg_table = hth_soup.find('table', attrs={'id': 'stats_games'})

        assert createdb.get_header(reg_table) == \
            [u'Rk',  u'Player', u'Date', u'Tm',  u'',    u'Opp', u'GS',
             u'MP',  u'FG',     u'FGA',  u'FGP', u'TP',  u'TPA', u'TPP',
             u'FT',  u'FTA',    u'FTP',  u'ORB', u'DRB', u'TRB', u'AST',
             u'STL', u'BLK',    u'TOV',  u'PF',  u'PTS']

    def test_get_hth_header_attribute_error(self):
        """
        Attempts to get header of non-existant Jason Kidd vs. Shabazz Napier
        regular season table.

        """
        gamelog_soup = createdb.soup_from_url(
            'http://www.basketball-reference.com/play-index/h2h_finder.cgi?' +
                'request=1&p1=kiddja01&p2=napiersh01#stats_playoffs')

        reg_table = gamelog_soup.findAll('table', attrs={'id': 'stats_games'})

        assert createdb.get_header(reg_table) is None

'''
class QueryTests(object):
    def __init__(self):
        self.calculate = Calculate(my_query, "DraftKings")
        self.queryhelpers = QueryHelpers(-365)

    def test_find_stats_none(self):
        stats = []
        self.calculate.find_stats('PTS')

    def test_remove_dnps_none(self):
        pass

    def test_remove_dnps(self):
        pass

    def test_stat_avg(self):
        pass

    def test_stat_avg_none(self):
        pass
'''
