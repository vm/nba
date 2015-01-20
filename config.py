import os


class Config(object):
    DEBUG = False
    TESTING = False
    USE_RELOADER = False
    CSRF_ENABLED = True
    SECRET_KEY = 'S00p3rS3cr3T'


class DevelopmentConfig(Config):
    """Local development config settings.
    """

    DEVELOPMENT = True
    DEBUG = True
    USE_RELOADER = True

    MONGODB_SETTINGS = {'DB': 'nba'}  # Default DB location for local use.
