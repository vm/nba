import json
from bson import json_util

from flask import render_template, request, Response

import query
from app import app
from utils import datetime_range


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/api/player', methods=['GET'])
def player():
    """
    The start of an API route, returns a player's data using ?name='x'.
    """
    name = request.args.get('name')
    player_dict = query.query_specific_player(name)
    player_dict.pop("_id", None)

    return Response(json.dumps(player_dict, default=json_util.default),
                    mimetype='application/json')


@app.route('/api/gamelogs', methods=['GET'])
def gamelogs():
    gamelogs_query = {}

    name = request.args.get('name')
    if name:
        gamelogs_query.update({'Player': name})
    start = request.args.get('start')
    end = request.args.get('end')
    if start:
        gamelogs_query.update(datetime_range(start, end))
    active = request.args.get('active')

    if not active:
        gamelogs_list = query.query_games(gamelogs_query)
    else:
        gamelogs_list = query.query_games(gamelogs_query, active=True)

    if gamelogs_list:
        for gamelog_dict in gamelogs_list:
            gamelog_dict.pop("_id", None)

    return Response(json.dumps(gamelogs_list, default=json_util.default),
                    mimetype='application/json')
