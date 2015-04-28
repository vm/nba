from . import ingest

def create(collection, update=True):
    ingest.CollectionCreator(collection, update=update).create()

