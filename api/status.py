import os
import sys
from flask import Flask, jsonify

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def status(path=''):
    config = server.load_config()
    res = {
        "configured": bool(config.get("client_id") and config.get("client_secret")),
        "authenticated": bool(config.get("refresh_token")),
        "region": config.get("region", "in"),
        "service": config.get("service", "recruit")
    }
    resp = jsonify(res)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp
