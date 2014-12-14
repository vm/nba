"""
This program scrapes basketball-reference to create a database of player
statistics. Stats for every year for every current player is added into the
gamelogs collection, every combination of player headtoheads's gamelogs are
added to headtoheads collection and salary data for current players are added
to salaries collection.

Todo:
    - Threading to download lots of pages at once.
"""

import create_db


def main():
    # print create_db.headtoheads_from_url('Kevin Durant', 'LeBron James')
    # print create_db.create_headtoheads_collection()
    # print create_db.gamelogs_from_url(
    #     'http://basketball-reference.com/players/b/bealbr01/gamelog/2014')
    # print create_db.create_gamelogs_collection()
    print create_db.create_salaries_collection()


if __name__ == '__main__':
    main()
