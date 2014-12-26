# Statcruncher: NBA API for Basketball-Reference

## Installation
''' sh
pip install -r requirements.txt
'''

Installation instructions for MongoDB. http://docs.mongodb.org/manual/tutorial/getting-started/

## Todo
- Threading to download lots of pages at once
- Add Twitter API to find inactives
- Add Draftkings/FanDuel daily prices (and projections?)
- Add salary data
- Create Flask-mongokit functions to get data from database
- Should I save Player as player_code or player name string?
- Raise errors instead of returning None?
- Create new find_player_code and the opposite