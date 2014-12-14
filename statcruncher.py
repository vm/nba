"""
This program scrapes basketball-reference to create a database player stats.
Stats for every year for every current player is added into the gamelogs
collection, every combination of player headtoheads's gamelogs are added to
headtoheads collection and salary data for current players are added to
salaries collection.

Todo:
    - Concurrency (multithreading) to download lots of pages at once.
"""

import create_db
import utils

from create_db import create_gamelog_collection


def main():
    # print create_db.hths_from_url('Kevin Durant', 'LeBron James')
    # print create_db.create_hth_collection()
    # print create_db.gamelogs_from_url(
    #     'http://www.basketball-reference.com/players/b/bealbr01/gamelog/2014')
    print create_gamelog_collection()


if __name__ == '__main__':
    main()
