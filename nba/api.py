from __future__ import absolute_import

from . import ingest

def create(collection, update=True):
    ingest.CollectionCreator(collection, update=update).create()
