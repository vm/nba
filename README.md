## NBA API for Player, Gamelog, Head-to-head data.

![westbrook.gif](http://cdn3.sbnation.com/assets/3914361/Russ-Troll.gif)

### Installation
Clone the repo.
```shell
$ git clone https://github.com/vigneshmohankumar/statcruncher.git
```

Install python requirements.
```shell
$ pip install -r requirements.txt
```

Install [MongoDB]( http://docs.mongodb.org/manual/tutorial/getting-started/).

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
- Create an actual API
- Split into multiple projects?
- Concurrency for createdb
- Twitter API to find inactives
- Draftkings/FanDuel daily data
- Add more data to Player (shooting hand, DOB, salary, etc.)
- Look into using stats.nba.com
- Raise errors instead of returning None?