import os


class Config(object):
    DEBUG = False
    TESTING = False
    USE_RELOADER = False
    CSRF_ENABLED = True
    SECRET_KEY = 'S00p3rS3cr3T'


class DevelopmentConfig(Config):
    """
    Local development config settings.
    """

    DEVELOPMENT = True
    DEBUG = True
    USE_RELOADER = True

    MONGODB_SETTINGS = {
        'DB': 'nba',
        'host': 'mongodb://localhost:27017/'
    }


class ProductionConfig(Config):
    """
    Heroku config settings.
    """

    DEBUG = False
    MONGODB_SETTINGS = {
        'DB': 'heroku_app33131232',
        'host': os.environ.get('MONGOLAB_URI', '')
    }

