from __future__ import (
	print_function, absolute_import, division, unicode_literals)

import os

from flask import Flask

from pymongo import MongoClient

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

connection = MongoClient(app.config['MONGODB_SETTINGS']['host'])
db = connection.nba
