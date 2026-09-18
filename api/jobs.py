import os
import sys
import time
from flask import Flask, jsonify

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def jobs(path=''):
    config = server.load_config()
    refresh_token = config.get("refresh_token")
    if not refresh_token:
        fallback = server.get_mock_fallback_data("Not Authorized. Showing demo data.")
        resp = jsonify(fallback)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    
    # Check if cache is empty or expired
    need_update = False
    with server.ZohoCache.lock:
        if server.ZohoCache.data is None or (time.time() - server.ZohoCache.last_updated > 300):
            need_update = True
            
    if need_update:
        server.update_zoho_cache(background=False)
            
    with server.ZohoCache.lock:
        if server.ZohoCache.data:
            resp = jsonify(server.ZohoCache.data)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        else:
            fallback = server.get_mock_fallback_data("Cache is empty. Showing demo data.", status="demo")
            resp = jsonify(fallback)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
