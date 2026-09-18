import os
import sys

# Add project root to sys.path so server.py and its dependencies can be resolved
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from server import OAuthProxyHandler

# Vercel Python runtime detects and invokes a BaseHTTPRequestHandler named 'handler'
class handler(OAuthProxyHandler):
    pass
