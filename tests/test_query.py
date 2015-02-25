import pytest

from nba.query import *

class TestQuery(object):
	def setup(self):
		pass

	def teardown(self):
		pass

	def test_query_specific_player_working(self):
		assert query_specific_player('Kobe Bryant') == 

	def test_query_specific_player_error(self):
		with pytest.raises(ValueError):
			query_specific_player('Vignesh Mohankumar')

	def test_query_games_working(self):
		assert query_games('Kobe Bryant') == 

	def test_query_games_none(self):
		with pytest.raises(ValueError):
			query_games('Vignesh Mohankumar')
