
from flask import Flask
# from flask.ext import restful
from flask.ext.mongoengine import MongoEngine

from statcruncher.settings import *


app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {'DB': 'nba'}

db = MongoEngine(app)
# api = restful.Api(app)

from statcruncher.urls import *

if __name__ == '__main__':
    app.run()
