import datetime

from nba.query import *


def test_create_datetime_range():
    assert datetime_range('2014-12-20', '2014-12-22') == {
        'Date': {
            '$gte': datetime.datetime(2014, 12, 20, 0, 0),
            '$lt': datetime.datetime(2014, 12, 22, 0, 0)
        }}
