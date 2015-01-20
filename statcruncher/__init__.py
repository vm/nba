import os

from flask import Flask
from flask.ext.mongokit import MongoKit


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


from statcruncher.routes import *

db = MongoKit(app)

if __name__ == "__main__":
    app.run()
