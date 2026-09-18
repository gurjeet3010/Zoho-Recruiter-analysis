import os
import sys
import json
import time
import urllib.request
import urllib.parse
from flask import Flask, request, Response

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

app = Flask(__name__)

def serve_error(message):
    error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Authorization Failed - TalentPulse</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #090b11;
            color: #f1f5f9;
            padding: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #111625;
            border: 1px solid #ef4444;
            border-radius: 16px;
            padding: 36px;
            max-width: 520px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        h1 {{ color: #ef4444; font-size: 22px; margin-bottom: 12px; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }}
        a {{
            background: #2563eb;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚠ Authorization Failed</h1>
        <p>{message}</p>
        <a href="/">Return to Dashboard</a>
    </div>
</body>
</html>
"""
    return Response(error_html, status=500, mimetype='text/html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def oauth_callback(path=''):
    code = request.args.get('code')
    if not code:
        return serve_error("Authorization code not found in callback query parameters.")
    
    config = server.load_config()
    region = config.get("region", "in")
    token_url = f"https://accounts.zoho.{region}/oauth/v2/token"
    
    proto = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('Host', request.host)
    redirect_uri = os.environ.get("ZOHO_REDIRECT_URI") or f"{proto}://{host}/oauth/callback"
    
    post_data = {
        "code": code,
        "client_id": config.get("client_id"),
        "client_secret": config.get("client_secret"),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    try:
        req_data = urllib.parse.urlencode(post_data).encode('utf-8')
        req = urllib.request.Request(token_url, data=req_data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            if "error" in res_body:
                return serve_error(f"Zoho Token Exchange Error: {res_body.get('error')}")
            
            config["refresh_token"] = res_body.get("refresh_token", config.get("refresh_token"))
            config["access_token"] = res_body.get("access_token")
            config["access_token_expires_at"] = time.time() + int(res_body.get("expires_in", 3600))
            server.save_config(config)
            
            sys.stdout.write(f"\n======================================\n")
            sys.stdout.write(f"ZOHO AUTHENTICATION SUCCESSFUL!\n")
            sys.stdout.write(f"ZOHO_REFRESH_TOKEN={config.get('refresh_token')}\n")
            sys.stdout.write(f"======================================\n\n")
            
            success_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Authorization Success - TalentPulse</title>
    <meta http-equiv="refresh" content="2;url=/" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #090b11;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            background: #111625;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 40px;
            max-width: 520px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }
        h1 {
            font-family: 'Outfit', sans-serif;
            color: #10b981;
            font-size: 24px;
            margin-bottom: 12px;
        }
        p { color: #94a3b8; font-size: 14px; line-height: 1.6; }
        .spinner {
            border: 3px solid rgba(255,255,255,0.1);
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border-left-color: #10b981;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-top: 24px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <h1>✓ Zoho Integration Authorized</h1>
        <p>Your session tokens have been initialized successfully. Redirecting you back to the TalentPulse Command Center...</p>
        <div class="spinner"></div>
    </div>
</body>
</html>
"""
            return Response(success_html, mimetype='text/html')
    except Exception as e:
        return serve_error(f"Failed to communicate with Zoho authorization servers: {str(e)}")
