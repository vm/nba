## NBA API for Player, Gamelog, Head-to-head data.

![nba.gif](http://www.nba.com/media/global/NBA_Twitter_default_logo.gif)

### Installation
Clone the repo.
```shell
git clone https://github.com/vm/nba-api.git
```

Install python requirements.
```shell
pip install -r requirements.txt
```

Install [MongoDB](http://docs.mongodb.org/manual/tutorial/getting-started/).
```shell
brew install mongodb
```

Install [Pathos](https://github.com/uqfoundation/pathos)
This one is kind of difficult. Basically, download each of these files and install them.
- [pyre](http://trac.mystic.cacr.caltech.edu/project/pathos/browser/pathos/external/pyre-0.8.2.0-pathos.zip?rev=674)
- [processing]()

Create all the data.
```python
from nba.ingest import *

CollectionCreator('players').create()
CollectionCreator('gamelogs', update=False).create()

# The combinations algorithm needs work, but this runs.
CollectionCreator('headtoheads').create()
```

### Usage
Initialize the server.
```shell
python main.py
```

Make a request.
```shell
curl 'http://127.0.0.1:5000/api/player?name=LeBron%20James'
curl 'http://127.0.0.1:5000/api/gamelogs?name=Stephen%20Curry&start=2012-05-07'
```
