from datetime import datetime
from mongokit import Connection, Document

connection = Connection()

@connection.register
class Gamelog(Document):
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
        'FTP': float,
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
        'FGP': float,
        'PlusMinus': float,
        'PTS': float,
        'Player': str,
        'MP': float,
        'Year': int,
        'ORB': float,
        'TPP': float
    }
    required_fields = ['Opp', 'G', 'Season', 'Age', 'HomeAway', 'Player',
                       'Tm', 'Year', 'Date', 'GS', 'WinLoss', 'Rk']
    use_dot_notation = True


@connection.register
class Headtohead(Document):
    __collection__ = 'headtoheads'
    structure = {
        'player_name_1': str,
        'player_name_2': str,
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
        'FTP': float,
        'Date': datetime,
        'PF': float,
        'WinLoss': float,
        'FGA': float,
        'GS': float,
        'STL': float,
        'TRB': float,
        'FTA': float,
        'BLK': float,
        'FGP': float,
        'PTS': float,
        'Player': str,
        'MP': float,
        'ORB': float,
        'TPP': float
    }
    required_fields = ['player_name_1', 'player_name_2', 'Opp', 'Season',
                       'HomeAway', 'Player', 'Tm', 'Date', 'GS', 'WinLoss',
                       'Rk']
    use_dot_notation = True


@connection.register
class Salary(Document):
    __collection__ = 'salaries'
    structure = {
        'Player': str,
        'Salary': dict
    }
    required_fields = ['Player', 'Salary']
    use_dot_notation = True
