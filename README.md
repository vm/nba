## NBA API for Player, Gamelog, Head-to-head data.

![westbrook.gif](http://www.nba.com/media/global/NBA_Twitter_default_logo.gif)

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
```shell
$ python
>>> from nba.ingest import (create_players_collection, create_gamelogs_collection,
        create_headtoheads_collection)
>>> create_players_collection()
>>> create_gamelogs_collection()
>>> create_headtoheads_collection()
```

### Usage
Initialize the server.
```shell
$ python manage.py runserver
```

Make a request.
```shell
$ curl 'http://localhost:5000/api/player?name=LeBron%20James'
```

### Todo
- Celery/async scraping
- Add more data to Player (shooting hand, DOB, salary, etc.)
- Look into using stats.nba.com
- Raise errors instead of returning None?