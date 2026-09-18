import os
import sys
import urllib.parse
from flask import Flask, request, redirect, Response

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server

app = Flask(__name__)

def serve_config_guide(host, proto):
    redirect_uri = os.environ.get("ZOHO_REDIRECT_URI") or f"{proto}://{host}/oauth/callback"
    guide_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TalentPulse - Zoho OAuth Configuration Required</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #090b11;
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .card {{
            background: #111625;
            border: 1px solid #1e293b;
            border-radius: 16px;
            max-width: 640px;
            width: 100%;
            padding: 36px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        .header-icon {{
            width: 52px;
            height: 52px;
            border-radius: 12px;
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: #f59e0b;
            margin-bottom: 20px;
        }}
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 10px;
        }}
        p.subtitle {{
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 24px;
        }}
        .instruction-box {{
            background: #0b0e17;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .instruction-title {{
            font-size: 13px;
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .variable-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .variable-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #151b2e;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 13px;
        }}
        .var-name {{ color: #38bdf8; font-weight: 600; }}
        .var-desc {{ color: #64748b; font-size: 12px; }}
        .redirect-uri-box {{
            background: #1e293b;
            padding: 10px 14px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            color: #10b981;
            word-break: break-all;
            margin-top: 6px;
        }}
        .actions {{
            display: flex;
            gap: 12px;
            margin-top: 28px;
        }}
        .btn {{
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .btn-primary {{
            background: #2563eb;
            color: white;
            border: none;
        }}
        .btn-primary:hover {{ background: #1d4ed8; }}
        .btn-secondary {{
            background: #1e293b;
            color: #cbd5e1;
            border: 1px solid #334155;
        }}
        .btn-secondary:hover {{ background: #334155; color: white; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header-icon"><i class="fa-solid fa-key"></i></div>
        <h1>Zoho OAuth Credentials Required</h1>
        <p class="subtitle">
            To connect with live Zoho Recruit data on Vercel, please configure your Zoho API credentials in your Vercel Project Dashboard.
        </p>
        
        <div class="instruction-box">
            <div class="instruction-title"><i class="fa-solid fa-gear"></i> Set Vercel Environment Variables:</div>
            <ul class="variable-list">
                <li class="variable-item">
                    <span class="var-name">ZOHO_CLIENT_ID</span>
                    <span class="var-desc">From Zoho API Console</span>
                </li>
                <li class="variable-item">
                    <span class="var-name">ZOHO_CLIENT_SECRET</span>
                    <span class="var-desc">From Zoho API Console</span>
                </li>
                <li class="variable-item">
                    <span class="var-name">ZOHO_REGION</span>
                    <span class="var-desc">in, com, eu, etc. (Default: in)</span>
                </li>
                <li class="variable-item">
                    <span class="var-name">ZOHO_REFRESH_TOKEN</span>
                    <span class="var-desc">(Optional) Skip re-login if already generated</span>
                </li>
            </ul>
        </div>

        <div class="instruction-box">
            <div class="instruction-title"><i class="fa-solid fa-link"></i> Authorized Redirect URI for Zoho API Console:</div>
            <div class="redirect-uri-box">{redirect_uri}</div>
        </div>

        <div class="actions">
            <a href="/" class="btn btn-primary"><i class="fa-solid fa-arrow-left"></i> Return to Dashboard</a>
            <a href="https://api-console.zoho.in" target="_blank" rel="noopener" class="btn btn-secondary"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open Zoho Console</a>
        </div>
    </div>
</body>
</html>
"""
    return Response(guide_html, mimetype='text/html', status=200)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def auth(path=''):
    proto = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('Host', request.host)
    
    config = server.load_config()
    client_id = config.get("client_id")
    
    # If client_id is not configured yet on Vercel, show the instructions page
    if not client_id:
        return serve_config_guide(host, proto)
    
    region = config.get("region", "in")
    accounts_domain = f"https://accounts.zoho.{region}"
    scopes = "ZohoRecruit.modules.ALL,ZohoRecruit.users.READ"
    
    redirect_uri = os.environ.get("ZOHO_REDIRECT_URI") or f"{proto}://{host}/oauth/callback"
    
    params = {
        "scope": scopes,
        "client_id": client_id,
        "response_type": "code",
        "access_type": "offline",
        "redirect_uri": redirect_uri,
        "prompt": "consent"
    }
    auth_url = f"{accounts_domain}/oauth/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)
