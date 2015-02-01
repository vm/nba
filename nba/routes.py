import json
from bson import json_util

from flask import jsonify, render_template, request, Response

import query
from . import app
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
    return Response(json.dumps(query.query_specific_player(name),
                               default=json_util.default),
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

    if active is None:
        gamelogs_list = query.query_games(gamelogs_query)
    else:
        gamelogs_list = query.query_games(gamelogs_query, active=True)

    return Response(json.dumps(gamelogs_list,
                               default=json_util.default),
                    mimetype='application/json')
