import ingest

def create(collection, update=True):
	ingest.Creator(collection, update=update).create()
