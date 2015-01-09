
import json

from bson import json_util
from flask import jsonify, render_template, request, Response

from metrics import query
from statcruncher import app


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/player')
def player():
    """The start of an API route, returns a player's data using ?name='x'.
    """
    name = request.args.get('name')
    p = query.QueryPlayers()

    return Response(json.dumps(p.query_specific_player(name),
        default=json_util.default), mimetype='application/json')