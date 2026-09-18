from flask import Flask, request, redirect, jsonify, Response
import os
import sys
import json
import time
import urllib.request
import urllib.parse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

# WSGI Middleware to restore the original path when Vercel rewrites to /api/index
class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        orig_path = (
            environ.get('HTTP_X_FORWARDED_URI') or
            environ.get('HTTP_X_MATCHED_PATH') or
            environ.get('HTTP_X_REWRITE_URL')
        )
        if orig_path:
            # Strip query parameters if present
            path_only = orig_path.split('?')[0]
            environ['PATH_INFO'] = path_only
        return self.wsgi_app(environ, start_response)

app = Flask(__name__)
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

def serve_error(message):
    error_html = f"""
    <html>
    <head><title>Authorization Failed</title></head>
    <body style="font-family: sans-serif; background-color: #090b11; color: #f1f5f9; padding: 40px; text-align: center;">
        <div style="background-color: #151b30; border: 1px solid #ef4444; border-radius: 12px; display: inline-block; padding: 30px; max-width: 500px;">
            <h1 style="color: #ef4444; margin-top:0;">⚠ Authorization Failed</h1>
            <p>{message}</p>
            <a href="/" style="background-color: #3b82f6; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top:20px;">Return to Dashboard</a>
        </div>
    </body>
    </html>
    """
    return Response(error_html, status=500, mimetype='text/html')

@app.route('/api/status', methods=['GET'])
@app.route('/status', methods=['GET'])
def api_status():
    config = server.load_config()
    status = {
        "configured": bool(config.get("client_id") and config.get("client_secret")),
        "authenticated": bool(config.get("refresh_token")),
        "region": config.get("region", "in"),
        "service": config.get("service", "recruit")
    }
    resp = jsonify(status)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/jobs', methods=['GET'])
@app.route('/jobs', methods=['GET'])
def api_jobs():
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

@app.route('/auth', methods=['GET'])
@app.route('/api/auth', methods=['GET'])
def auth():
    config = server.load_config()
    region = config.get("region", "in")
    accounts_domain = f"https://accounts.zoho.{region}"
    scopes = "ZohoRecruit.modules.ALL,ZohoRecruit.users.READ"
    
    proto = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('Host', request.host)
    redirect_uri = f"{proto}://{host}/oauth/callback"
    
    params = {
        "scope": scopes,
        "client_id": config.get("client_id"),
        "response_type": "code",
        "access_type": "offline",
        "redirect_uri": redirect_uri,
        "prompt": "consent"
    }
    auth_url = f"{accounts_domain}/oauth/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/oauth/callback', methods=['GET'])
@app.route('/api/oauth/callback', methods=['GET'])
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return serve_error("Authorization code not found in callback query params.")
    
    config = server.load_config()
    region = config.get("region", "in")
    token_url = f"https://accounts.zoho.{region}/oauth/v2/token"
    
    proto = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('Host', request.host)
    redirect_uri = f"{proto}://{host}/oauth/callback"
    
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
            
            success_html = """
            <html>
            <head>
                <title>Authorization Success</title>
                <meta http-equiv="refresh" content="2;url=/" />
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #090b11; color: #f1f5f9; text-align: center; padding-top: 100px; }
                    .card { background-color: #151b30; border: 1px solid #242c4b; border-radius: 12px; display: inline-block; padding: 40px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
                    h1 { color: #10b981; margin-bottom: 10px; }
                    p { color: #94a3b8; }
                    .spinner { border: 4px solid rgba(255,255,255,0.1); width: 36px; height: 36px; border-radius: 50%; border-left-color: #10b981; animation: spin 1s linear infinite; display: inline-block; margin-top: 20px; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>✓ Zoho Integration Authorized</h1>
                    <p>Credentials saved successfully. Redirecting you back to the TalentPulse Dashboard...</p>
                    <div class="spinner"></div>
                </div>
            </body>
            </html>
            """
            return Response(success_html, mimetype='text/html')
    except Exception as e:
        return serve_error(f"Failed to communicate with Zoho authorization servers: {str(e)}")

# Catch-all and fallback handler for direct /api/index invocations
@app.route('/api/index', methods=['GET'])
@app.route('/api', methods=['GET'])
def api_root_dispatcher():
    # If the request reached here directly, check original path or query params
    orig_path = (
        request.headers.get('X-Forwarded-Uri') or
        request.headers.get('X-Matched-Path') or
        request.headers.get('X-Rewrite-Url') or ''
    )
    if '/auth' in orig_path:
        return auth()
    elif '/oauth/callback' in orig_path:
        return oauth_callback()
    elif '/api/status' in orig_path or '/status' in orig_path:
        return api_status()
    elif '/api/jobs' in orig_path or '/jobs' in orig_path:
        return api_jobs()
    return api_jobs()
