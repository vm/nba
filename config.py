
import os

class Config(object):

    DEBUG = False
    TESTING = False
    USE_RELOADER = False
    CSRF_ENABLED = True
    SECRET_KEY = 'S00p3rS3cr3T'


class ProductionConfig(Config):
    """Heroku config settings.
    """

    DEBUG = False
    MONGODB_SETTINGS = {'DB': 'heroku_app33131232',
                        'host': os.environ['MONGOLAB_URI']}


class DevelopmentConfig(Config):
    """Local development config settings.
    """

    DEVELOPMENT = True
    DEBUG = True
    USE_RELOADER = True

    MONGODB_SETTINGS = {'DB': 'nba'} ## default DB location for local use.