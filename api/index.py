import os
import sys
from flask import Flask, request, send_from_directory

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.auth import auth
from api.callback import oauth_callback
from api.jobs import jobs
from api.status import status

app = Flask(__name__)

# Register exact API routes
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

# Root route serves the visual dashboard HTML
@app.route('/', methods=['GET'])
def route_index():
    return send_from_directory(BASE_DIR, 'index.html')

# Catch-all route for static assets and API fallbacks
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path=''):
    clean_path = (path or '').strip('/')
    
    # 1. Check if a static file exists at the project root (e.g. style.css, app.js, data.js, index.html)
    static_file = os.path.join(BASE_DIR, clean_path)
    if clean_path and os.path.isfile(static_file):
        return send_from_directory(BASE_DIR, clean_path)
    
    # 2. Check if route matches known API endpoints
    low_path = clean_path.lower()
    if 'auth' in low_path:
        return auth()
    elif 'callback' in low_path:
        return oauth_callback()
    elif 'status' in low_path:
        return status()
    elif 'job' in low_path:
        return jobs()
    
    # 3. Default fallback to the dashboard HTML
    return send_from_directory(BASE_DIR, 'index.html')
