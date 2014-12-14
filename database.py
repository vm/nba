from datetime import datetime
from flask import Flask
from flask import Flask, request, render_template, redirect, url_for
from flask.ext.mongokit import MongoKit, Document
from mongokit import Connection, Document


app = Flask(__name__)
db = MongoKit(app)

class Gamelog(Document):
    __collection__ = 'gamelogs'
    structure = {
        u'FT': float,
        u'TP': float,
        u'TOV': float,
        u'Tm': str,
        u'GmSc': str,
        u'FG': float,
        u'TPA': float,
        u'DRB': float,
        u'Rk': float,
        u'Opp': str,
        u'AST': float,
        u'Season': str,
        u'HomeAway': str,
        u'FTP': float,
        u'Date': datetime,
        u'PF': float,
        u'WinLoss': float,
        u'FGA': float,
        u'GS': float,
        u'G': float,
        u'STL': float,
        u'Age': str,
        u'TRB': float,
        u'FTA': float,
        u'BLK': float,
        u'FGP': float,
        u'PlusMinus': float,
        u'PTS': float,
        u'Player': str,
        u'MP': float,
        u'Year': int,
        u'ORB': float,
        u'TPP': float
    }
    required_fields = ['Opp', 'G', 'Season', 'Age', 'HomeAway', 'Player',
                       'Tm', 'Year', 'Date', 'GS', 'WinLoss', 'Rk']
    use_dot_notation = True

    def __repr__(self):
        return '<User %r>' % (self.name)


class Headtohead(Document):
    __collection__ = 'headtoheads'
    structure = {
        u'FT': float,
        u'TP': float,
        u'TOV': float,
        u'Tm': str,
        u'GmSc': str,
        u'FG': float,
        u'TPA': float,
        u'DRB': float,
        u'Rk': float,
        u'Opp': str,
        u'AST': float,
        u'Season': str,
        u'HomeAway': str,
        u'FTP': float,
        u'Date': datetime,
        u'PF': float,
        u'WinLoss': float,
        u'FGA': float,
        u'GS': float,
        u'G': float,
        u'STL': float,
        u'Age': str,
        u'TRB': float,
        u'FTA': float,
        u'BLK': float,
        u'FGP': float,
        u'PlusMinus': float,
        u'PTS': float,
        u'Player': str,
        u'MP': float,
        u'Year': int,
        u'ORB': float,
        u'TPP': float
    }
    required_fields = ['Opp', 'G', 'Season', 'Age', 'HomeAway', 'Player',
                       'Tm', 'Year', 'Date', 'GS', 'WinLoss', 'Rk']
    use_dot_notation = True

    def __repr__(self):
        return '<User %r>' % (self.name)


class Salary(Document):
    __collection__ = 'salaries'
    structure = {
        u'Player': str,
        u'Salary': dict
    }
    required_fields = ['Player', 'Salary']
    use_dot_notation = True

    def __repr__(self):
        return '<User %r>' % (self.name)

db.register([Gamelog, Headtohead])

@app.errorhandler(400)
def bad_request(error):
    return "Bad Request", 400


@app.route('/')
def index():
    return "Hello...world?"


if __name__ == '__main__':
    app.run(host='0.0.0.0')
