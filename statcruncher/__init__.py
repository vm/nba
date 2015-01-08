
from flask import Flask
# from flask.ext.mongoengine import MongoEngine

from statcruncher.settings import *


app = Flask(__name__)
# app.config['MONGODB_SETTINGS'] = {'DB': 'bookviz'}
# app.config['SECRET_KEY'] = settings.SECRET_KEY

# db = MongoEngine(app)


from statcruncher.urls import *
# from statcruncher.models import *


if __name__ == '__main__':
    app.run()
