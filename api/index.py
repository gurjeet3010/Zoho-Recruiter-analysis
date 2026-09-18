import os
import sys
from flask import Flask, request

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.auth import auth
from api.callback import oauth_callback
from api.jobs import jobs
from api.status import status

app = Flask(__name__)

# Register exact routes
@app.route('/api/auth', methods=['GET'])
@app.route('/auth', methods=['GET'])
def route_auth():
    return auth()

@app.route('/api/callback', methods=['GET'])
@app.route('/oauth/callback', methods=['GET'])
def route_callback():
    return oauth_callback()

@app.route('/api/jobs', methods=['GET'])
@app.route('/jobs', methods=['GET'])
def route_jobs():
    return jobs()

@app.route('/api/status', methods=['GET'])
@app.route('/status', methods=['GET'])
def route_status():
    return status()

# Catch-all dispatcher to ensure no route ever 404s inside Flask
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path=''):
    target = (path or '').lower()
    orig = (
        request.headers.get('X-Forwarded-Uri') or
        request.headers.get('X-Matched-Path') or
        request.headers.get('X-Rewrite-Url') or
        request.path or ''
    ).lower()

    combined = f"{target} {orig}"

    if 'auth' in combined:
        return auth()
    elif 'callback' in combined:
        return oauth_callback()
    elif 'status' in combined:
        return status()
    else:
        return jobs()
