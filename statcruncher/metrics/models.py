import os
from datetime import datetime

from mongokit import Connection, Document

connection = Connection(
    os.environ.get('MONGOLAB_URI', 'mongodb://localhost:27017'))


@connection.register
class Gamelog(Document):
    __database__ = 'nba'
    __collection__ = 'gamelogs'
    structure = {
        'FT': float,
        'TP': float,
        'TOV': float,
        'Tm': str,
        'GmSc': str,
        'FG': float,
        'TPA': float,
        'DRB': float,
        'Rk': float,
        'Opp': str,
        'AST': float,
        'Season': str,
        'HomeAway': str,
        'Date': datetime,
        'PF': float,
        'WinLoss': float,
        'FGA': float,
        'GS': float,
        'G': float,
        'STL': float,
        'Age': str,
        'TRB': float,
        'FTA': float,
        'BLK': float,
        'PlusMinus': float,
        'PTS': float,
        'Player': str,
        'PlayerCode': str,
        'MP': float,
        'Year': int,
        'ORB': float
    }
    required_fields = [
        'Opp', 'Season', 'G', 'Age', 'HomeAway', 'Player', 'Tm', 'Year', 'Rk',
        'GS',  'WinLoss',  'Date', 'PlayerCode'
    ]
    use_dot_notation = True


@connection.register
class Headtohead(Document):
    __database__ = 'nba'
    __collection__ = 'headtoheads'
    structure = {
        'MainPlayer': str,
        'MainPlayerCode': str,
        'OppPlayer': str,
        'OppPlayerCode': str,
        'FT': float,
        'TP': float,
        'TOV': float,
        'Tm': str,
        'FG': float,
        'TPA': float,
        'DRB': float,
        'Rk': float,
        'Opp': str,
        'AST': float,
        'Season': str,
        'HomeAway': str,
        'Date': datetime,
        'PF': float,
        'WinLoss': float,
        'FGA': float,
        'GS': float,
        'STL': float,
        'TRB': float,
        'FTA': float,
        'BLK': float,
        'PTS': float,
        'MP': float,
        'ORB': float
    }
    required_fields = [
        'MainPlayer', 'MainPlayerCode', 'OppPlayer', 'OppPlayerCode',
        'Season', 'WinLoss', 'HomeAway', 'GS', 'Date', 'Rk', 'Tm'
    ]
    use_dot_notation = True


@connection.register
class Player(Document):
    __database__ = 'nba'
    __collection__ = 'players'
    structure = {
        'Player': str,
        'Salary': dict,
        'URL': str,
        'GamelogURLs': list
    }
    required_fields = ['Player', 'URL', 'GamelogURLs']
    use_dot_notation = True
