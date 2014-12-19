import json
import pickle

from create_db import (find_gamelogs_from_url, find_basic_gamelogs_from_url,
    find_headtohead_gamelogs_from_url, add_gamelogs_in_table_to_db,
    create_gamelogs_collection, create_headtoheads_collection)
from utils import (find_player_code, get_header, is_number,
    path_components_of_url, soup_from_url)


def test_is_number_true():
    assert is_number('5') is True


def test_is_number_false():
    assert is_number('MIA') is False


def test_path_list_from_url():
    path_list = ['', 'players', 'd', 'duranke01', 'gamelog', '2014', '']
    assert path_components_of_url(
        'http://www.basketball-reference.com/players/d/duranke01/' +
            'gamelog/2014/') == path_list


def test_find_player_code_real_player():
    assert find_player_code('Barack Obama') is None


def test_find_player_code_imaginary_player():
    assert find_player_code('Kevin Durant') == 'duranke01'


def test_get_gamelog_header():
    gamelog_soup = soup_from_url(
        'http://www.basketball-reference.com/players/d/duranke01/' +
            'gamelog/2015/')

    reg_table = gamelog_soup.find(
        'table', attrs={'id': 'pgl_basic'})

    assert get_header(reg_table) == \
        [u'Rk', u'G', u'Date', u'Age', u'Tm', u'', u'Opp', u'GS', u'MP',
         u'FG', u'FGA', u'FGP', u'TP', u'TPA', u'TPP', u'FT', u'FTA',
         u'FTP', u'ORB', u'DRB', u'TRB', u'AST', u'STL', u'BLK', u'TOV',
         u'PF', u'PTS', u'GmSc', u'PlusMinus']


def test_get_hth_header():
    hth_soup = soup_from_url(
        'http://www.basketball-reference.com/play-index/h2h_finder.cgi?' +
            'request=1&p1=jamesle01&p2=duranke01#stats_playoffs')

    reg_table = hth_soup.find(
        'table', attrs={'id': 'stats_games'})

    assert get_header(reg_table) == \
        [u'Rk', u'Player', u'Date', u'Tm', u'', u'Opp', u'GS', u'MP',
         u'FG', u'FGA', u'FGP', u'TP', u'TPA', u'TPP', u'FT', u'FTA',
         u'FTP', u'ORB', u'DRB', u'TRB', u'AST', u'STL', u'BLK', u'TOV',
         u'PF', u'PTS']


def test_get_hth_header_attribute_error():
    """
    Tries to get header of non-existant Jason Kidd vs. Shabazz Napier
    regular season table.

    """

    gamelog_soup = soup_from_url(
        'http://www.basketball-reference.com/play-index/h2h_finder.cgi?' +
            'request=1&p1=kiddja01&p2=napiersh01#stats_playoffs')

    reg_table = gamelog_soup.findAll(
        'table', attrs={'id': 'stats_games'})

    assert get_header(reg_table) is None


'''def test_gamelogs_from_url_real():'''

'''
class TestCreateDatabase(object):
    def test_gamelogs_from_url:
'''
