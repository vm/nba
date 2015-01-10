
import os

from flask import Flask
from flask.ext.mongoengine import MongoEngine

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

db = MongoEngine(app)

from statcruncher.urls import *

if __name__ == "__main__":
    app.run()
