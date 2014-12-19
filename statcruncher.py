"""
This program scrapes basketball-reference to create a database of player
statistics. Stats for every year for every current player is added into the
gamelogs collection, every combination of player headtoheads's gamelogs are
added to headtoheads collection and salary data for current players are added
to salaries collection.

Todo:
    - Threading to download lots of pages at once.
    - Add Twitter API to find inactives
    - Add Draftkings/FanDuel daily prices (and projections?)
    - Add salary data
    - Create functions to calculate stats from data
    - Instead of p1, p2, player in headtoheads, remove Player if it is the
      same as p1; otherwise, convert p1 to Player and p2 to p1
    - Create Flask-mongokit functions to get data from database
    - Should I save Player as player_code or player name string?
    - Raise errors instead of returning None?
"""

import sys

from create_db import (find_gamelogs_from_url, find_basic_gamelogs_from_url,
    find_headtohead_gamelogs_from_url, create_gamelogs_collection,
    create_headtoheads_collection)


def main():
    pass


if __name__ == '__main__':
    main(sys.argv)
