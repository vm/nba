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

Install [MongoDB]( http://docs.mongodb.org/manual/tutorial/getting-started/).
```shell
brew install mongodb
```

Create all the data.
```python
from nba.ingest import *

create_players_collection()
create_gamelogs_collection(update=False)
create_headtoheads_collection()  # This basically never ends. I'll fix that.
```

### Usage
Initialize the server.
```shell
python manage.py runserver
```

Make a request.
```shell
curl 'http://127.0.0.1:5000/api/player?name=LeBron%20James'
curl 'http://127.0.0.1:5000/api/gamelogs?name=Stephen%20Curry&start=2012-05-07'
```

### Todo
- Celery/async scraping
- Add more data to Player (shooting hand, DOB, salary, etc.)
- Look into using stats.nba.com
- Raise errors instead of returning None?
