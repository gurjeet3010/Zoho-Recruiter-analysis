import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import sys
import time
import mimetypes
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8123))
CONFIG_FILE = os.path.join(BASE_DIR, ".config.json")

# Load .env file manually if it exists to avoid requiring external packages
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Re-read PORT in case it was defined in .env
PORT = int(os.environ.get("PORT", PORT))

class ZohoCache:
    data = None
    last_updated = 0
    is_updating = False
    lock = threading.Lock()

def get_config_file():
    # If running on Vercel or serverless where filesystem is read-only, use /tmp
    if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
        return os.path.join("/tmp", ".config.json")
    return CONFIG_FILE

# Load initial config
def load_config():
    # Load environment configuration (precedence for Vercel / Render / .env variables)
    env_config = {
        "client_id": os.environ.get("ZOHO_CLIENT_ID"),
        "client_secret": os.environ.get("ZOHO_CLIENT_SECRET"),
        "region": os.environ.get("ZOHO_REGION"),
        "service": os.environ.get("ZOHO_SERVICE"),
        "refresh_token": os.environ.get("ZOHO_REFRESH_TOKEN"),
        "access_token": os.environ.get("ZOHO_ACCESS_TOKEN"),
        "access_token_expires_at": int(float(os.environ.get("ZOHO_ACCESS_TOKEN_EXPIRES_AT"))) if os.environ.get("ZOHO_ACCESS_TOKEN_EXPIRES_AT") else None
    }
    # Clean none keys
    env_config = {k: v for k, v in env_config.items() if v is not None}

    # Load file configuration
    file_config = {}
    target_cfg = get_config_file()
    # Try primary config path
    if os.path.exists(target_cfg):
        try:
            with open(target_cfg, 'r') as f:
                file_config = json.load(f)
        except Exception:
            pass
    # Fallback to base dir config if target was /tmp and not found yet
    if not file_config and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
        except Exception:
            pass

    config = {
        "client_id": "",
        "client_secret": "",
        "region": "in",
        "service": "recruit",
        "refresh_token": "",
        "access_token": "",
        "access_token_expires_at": 0
    }
    config.update(env_config)
    config.update(file_config)
    return config

def save_config(config):
    target_cfg = get_config_file()
    try:
        with open(target_cfg, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not save config file to {target_cfg}: {e}\n")

class OAuthProxyHandler(http.server.BaseHTTPRequestHandler):
    
    def get_redirect_uri(self):
        host = self.headers.get('Host', f'127.0.0.1:{PORT}')
        proto = self.headers.get('X-Forwarded-Proto', 'http')
        return f"{proto}://{host}/oauth/callback"

    def log_message(self, format, *args):
        # Override to log cleanly to stderr without disrupting shell output
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API Status Endpoint
        if path == "/api/status":
            self.handle_api_status()
        
        # 2. API Jobs Endpoint
        elif path == "/api/jobs":
            self.handle_api_jobs()
            
        # 3. Trigger Zoho Authentication
        elif path == "/auth":
            self.handle_auth_redirect()
            
        # 4. OAuth Callback Handler
        elif path == "/oauth/callback":
            self.handle_oauth_callback(query)
            
        # 5. Static Files Serving
        else:
            self.serve_static_file(path)

    def handle_api_status(self):
        config = load_config()
        status = {
            "configured": bool(config.get("client_id") and config.get("client_secret")),
            "authenticated": bool(config.get("refresh_token")),
            "region": config.get("region", "in"),
            "service": config.get("service", "recruit")
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode('utf-8'))

    def handle_auth_redirect(self):
        config = load_config()
        region = config.get("region", "in")
        accounts_domain = f"https://accounts.zoho.{region}"
        
        # Scopes required for Zoho Recruit: job openings, candidates read operations
        scopes = "ZohoRecruit.modules.ALL,ZohoRecruit.users.READ"
        
        params = {
            "scope": scopes,
            "client_id": config.get("client_id"),
            "response_type": "code",
            "access_type": "offline",
            "redirect_uri": self.get_redirect_uri(),
            "prompt": "consent"
        }
        
        auth_url = f"{accounts_domain}/oauth/v2/auth?{urllib.parse.urlencode(params)}"
        
        self.send_response(302)
        self.send_header('Location', auth_url)
        self.end_headers()

    def handle_oauth_callback(self, query):
        code_list = query.get('code')
        if not code_list:
            self.serve_error("Authorization code not found in callback query params.")
            return
            
        code = code_list[0]
        config = load_config()
        region = config.get("region", "in")
        token_url = f"https://accounts.zoho.{region}/oauth/v2/token"
        
        # Exchange authorization code for access & refresh tokens
        post_data = {
            "code": code,
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret"),
            "redirect_uri": self.get_redirect_uri(),
            "grant_type": "authorization_code"
        }
        
        try:
            req_data = urllib.parse.urlencode(post_data).encode('utf-8')
            req = urllib.request.Request(token_url, data=req_data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                
                if "error" in res_body:
                    self.serve_error(f"Zoho Token Exchange Error: {res_body.get('error')}")
                    return
                
                # Save credentials to config
                config["refresh_token"] = res_body.get("refresh_token", config.get("refresh_token"))
                config["access_token"] = res_body.get("access_token")
                config["access_token_expires_at"] = time.time() + int(res_body.get("expires_in", 3600))
                save_config(config)

                # Print to logs for persistent hosting
                sys.stdout.write(f"\n======================================\n")
                sys.stdout.write(f"ZOHO AUTHENTICATION SUCCESSFUL!\n")
                sys.stdout.write(f"Configure this variable in Render Environment settings to keep it connected:\n")
                sys.stdout.write(f"ZOHO_REFRESH_TOKEN={config.get('refresh_token')}\n")
                sys.stdout.write(f"======================================\n\n")
                
                # Redirect back to dashboard homepage
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
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
                self.wfile.write(success_html.encode('utf-8'))
        except Exception as e:
            self.serve_error(f"Failed to communicate with Zoho authorization servers: {str(e)}")

    def handle_api_jobs(self):
        config = load_config()
        refresh_token = config.get("refresh_token")
        
        # Fallback to Mock Data if not authorized
        if not refresh_token:
            self.serve_fallback_data("Not Authorized. Showing demo data.")
            return
            
        # Check Cache
        need_bg_update = False
        with ZohoCache.lock:
            if ZohoCache.data is None:
                # If running on Vercel or serverless, do synchronous fetch
                if os.environ.get("VERCEL"):
                    self.update_zoho_cache(background=False)
                    if ZohoCache.data:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(ZohoCache.data).encode('utf-8'))
                        return
                else:
                    self.update_zoho_cache(background=True)
                self.serve_fallback_data("Cache is empty. Syncing with Zoho in background...", status="demo")
                return
            elif time.time() - ZohoCache.last_updated > 300: # 5 minutes expiry
                # Cache is expired, update, serve stale data for now
                need_bg_update = True
                
        if need_bg_update:
            self.update_zoho_cache(background=not bool(os.environ.get("VERCEL")))
            
        # Serve Cache
        with ZohoCache.lock:
            if ZohoCache.data:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(ZohoCache.data).encode('utf-8'))
            else:
                self.serve_fallback_data("Cache is empty. Showing demo data.", status="demo")

    def get_valid_access_token(self, config):
        # Return current token if it has at least 30 seconds before expiration
        if config.get("access_token") and config.get("access_token_expires_at", 0) > time.time() + 30:
            return config["access_token"]
            
        # Refresh token exchange
        region = config.get("region", "in")
        token_url = f"https://accounts.zoho.{region}/oauth/v2/token"
        
        post_data = {
            "refresh_token": config.get("refresh_token"),
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret"),
            "grant_type": "refresh_token"
        }
        
        try:
            req_data = urllib.parse.urlencode(post_data).encode('utf-8')
            req = urllib.request.Request(token_url, data=req_data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                if "access_token" in res_body:
                    config["access_token"] = res_body["access_token"]
                    config["access_token_expires_at"] = time.time() + int(res_body.get("expires_in", 3600))
                    save_config(config)
                    return config["access_token"]
        except Exception as e:
            sys.stderr.write(f"Failed to refresh access token: {str(e)}\n")
        return None

    def update_zoho_cache(self, background=True):
        def run_update():
            with ZohoCache.lock:
                if ZohoCache.is_updating:
                    return
                ZohoCache.is_updating = True
            
            try:
                sys.stdout.write("Refreshing Zoho cache...\n")
                config = load_config()
                region = config.get("region", "in")
                access_token = self.get_valid_access_token(config)
                if not access_token:
                    sys.stderr.write("Cache update aborted: Invalid access token.\n")
                    return
                # 1. Fetch all applications
                actual_pipelines = {}
                actual_sources = {}
                global_hires = 0
                total_applications_count = 0
                page = 1
                while True:
                    url = f"https://recruit.zoho.{region}/recruit/v2/Applications?per_page=100&page={page}"
                    req = urllib.request.Request(url)
                    req.add_header('Authorization', f'Zoho-oauthtoken {access_token}')
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res_body = json.loads(resp.read().decode('utf-8'))
                        data = res_body.get("data", [])
                        if not data:
                            break
                        total_applications_count += len(data)
                        for app in data:
                            job_db_id = app.get("$Job_Opening_Id")
                            stage = app.get("Hiring_Pipeline") or ""
                            stage_lower = stage.lower()
                            
                            if "hired" in stage_lower or "hire" in stage_lower:
                                global_hires += 1
                                
                            if not job_db_id:
                                continue
                            job_db_id = str(job_db_id)
                            
                            if job_db_id not in actual_pipelines:
                                actual_pipelines[job_db_id] = {
                                    "screening": 0, "interview": 0, "offered": 0, "rejected": 0, "archived": 0, "hired": 0
                                }
                            if job_db_id not in actual_sources:
                                actual_sources[job_db_id] = {
                                    "naukri": 0, "linkedin": 0, "referral": 0, "website": 0
                                }
                            
                            if "screening" in stage_lower or "screen" in stage_lower:
                                actual_pipelines[job_db_id]["screening"] += 1
                            elif "interview" in stage_lower:
                                actual_pipelines[job_db_id]["interview"] += 1
                            elif "offered" in stage_lower or "offer" in stage_lower:
                                actual_pipelines[job_db_id]["offered"] += 1
                            elif "hired" in stage_lower or "hire" in stage_lower:
                                actual_pipelines[job_db_id]["hired"] += 1
                            elif "archive" in stage_lower:
                                actual_pipelines[job_db_id]["archived"] += 1
                            elif "reject" in stage_lower or "unqualified" in stage_lower:
                                actual_pipelines[job_db_id]["rejected"] += 1
                            else:
                                actual_pipelines[job_db_id]["screening"] += 1
                                
                            source = app.get("Application_Source") or ""
                            source_lower = source.lower()
                            if "linkedin" in source_lower:
                                actual_sources[job_db_id]["linkedin"] += 1
                            elif "refer" in source_lower or "employee" in source_lower:
                                actual_sources[job_db_id]["referral"] += 1
                            elif "naukri" in source_lower or "website" in source_lower or "career" in source_lower or "portal" in source_lower:
                                actual_sources[job_db_id]["website"] += 1
                            else:
                                actual_sources[job_db_id]["linkedin"] += 1
                                
                        if not res_body.get("info", {}).get("more_records", False):
                            break
                        page += 1

                # 2. Fetch Interviews and categorize them
                interviews_completed = 0
                interviews_cancelled = 0
                interviews_pending = 0
                interview_hires = 0
                page = 1
                while True:
                    url = f"https://recruit.zoho.{region}/recruit/v2/Interviews?per_page=100&page={page}"
                    req = urllib.request.Request(url)
                    req.add_header('Authorization', f'Zoho-oauthtoken {access_token}')
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            res_body = json.loads(resp.read().decode('utf-8'))
                            data = res_body.get("data", [])
                            if not data:
                                break
                            for item in data:
                                status = item.get("Interview_Status") or "None"
                                if status in ['Hired', 'Strong Hire']:
                                    interviews_completed += 1
                                    if status == 'Hired':
                                        interview_hires += 1
                                elif status == 'Rejected':
                                    interviews_cancelled += 1
                                elif status in ['Shortlist', 'On-Hold', 'Move to next round', 'None']:
                                    interviews_pending += 1
                            if not res_body.get("info", {}).get("more_records", False):
                                break
                            page += 1
                    except Exception as e:
                        sys.stderr.write(f"Error fetching interviews: {e}\n")
                        break

                # 3. Fetch Submissions
                submissions_count = 0
                page = 1
                while True:
                    url = f"https://recruit.zoho.{region}/recruit/v2/Submissions?per_page=100&page={page}"
                    req = urllib.request.Request(url)
                    req.add_header('Authorization', f'Zoho-oauthtoken {access_token}')
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            res_body = json.loads(resp.read().decode('utf-8'))
                            data = res_body.get("data", [])
                            if not data:
                                break
                            submissions_count += len(data)
                            if not res_body.get("info", {}).get("more_records", False):
                                break
                            page += 1
                    except:
                        break

                # 4. Fetch Offers and categorize them
                offers_accepted = 0
                offers_declined = 0
                offers_pending = 0
                page = 1
                while True:
                    url = f"https://recruit.zoho.{region}/recruit/v2/Offers?per_page=100&page={page}"
                    req = urllib.request.Request(url)
                    req.add_header('Authorization', f'Zoho-oauthtoken {access_token}')
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            res_body = json.loads(resp.read().decode('utf-8'))
                            data = res_body.get("data", [])
                            if not data:
                                break
                            for item in data:
                                status = item.get("Status") or "None"
                                if status == 'Offer accepted':
                                    offers_accepted += 1
                                elif status in ['Offer declined', 'Offer withdrawn']:
                                    offers_declined += 1
                                elif status == 'Offer made':
                                    offers_pending += 1
                            if not res_body.get("info", {}).get("more_records", False):
                                break
                            page += 1
                    except Exception as e:
                        sys.stderr.write(f"Error fetching offers: {e}\n")
                        break
                                
                # 5. Fetch job openings
                recruit_api_url = f"https://recruit.zoho.{region}/recruit/v2/Job_Openings?per_page=200"
                req = urllib.request.Request(recruit_api_url)
                req.add_header('Authorization', f'Zoho-oauthtoken {access_token}')
                with urllib.request.urlopen(req, timeout=10) as resp:
                    res_body = json.loads(resp.read().decode('utf-8'))
                    jobs_data = res_body.get("data", [])
                    
                    # Filter: Only In-progress openings are active
                    active_jobs = [j for j in jobs_data if j.get("Job_Opening_Status") == "In-progress"]
                    
                    mapped_jobs = []
                    for index, record in enumerate(active_jobs):
                        job_id = record.get("id")
                        job_code = record.get("Job_Opening_ID") or job_id
                        job_title = record.get("Posting_Title") or record.get("Job_Opening_Name") or record.get("Job_Title") or record.get("Name") or "Untitled Position"
                        company = record.get("Company") or record.get("Client_Name") or "Enterprise Client"
                        
                        dept_obj = record.get("Department_Name")
                        department = "Engineering"
                        if dept_obj and isinstance(dept_obj, dict):
                            department = dept_obj.get("name", "Engineering")
                        elif record.get("Department"):
                            department = record.get("Department")
                            
                        try:
                            positions = int(record.get("Number_of_Positions", 1))
                        except:
                            positions = 1
                            
                        target_date = record.get("Target_Date") or "2026-08-30"
                        
                        days_open = 5
                        created_time = record.get("Created_Time")
                        if created_time:
                            try:
                                date_part = created_time.split('T')[0]
                                created_epoch = time.mktime(time.strptime(date_part, "%Y-%m-%d"))
                                days_open = max(1, int((time.time() - created_epoch) / (24 * 3600)))
                            except:
                                pass
                                
                        status = "Delayed" if days_open > 20 else "On Track"
                        
                        recruiter_obj = record.get("Assigned_Recruiter") or record.get("Owner")
                        recruiter_name = "Lead Talent Partner"
                        if recruiter_obj:
                            if isinstance(recruiter_obj, list) and len(recruiter_obj) > 0:
                                first_rec = recruiter_obj[0]
                                if isinstance(first_rec, dict):
                                    recruiter_name = first_rec.get("name", "Lead Talent Partner")
                            elif isinstance(recruiter_obj, dict):
                                recruiter_name = recruiter_obj.get("name", "Lead Talent Partner")
                                
                        next_action = record.get("Next_Action") or "No action recorded"
                                
                        pipeline = actual_pipelines.get(str(job_id), {
                            "screening": 0, "interview": 0, "offered": 0, "rejected": 0, "hired": 0
                        })
                        sources = actual_sources.get(str(job_id), {
                            "naukri": 0, "linkedin": 0, "referral": 0, "website": 0
                        })
                        
                        mapped_jobs.append({
                            "id": str(job_id),
                            "jobCode": str(job_code),
                            "companyName": company,
                            "jobTitle": job_title,
                            "department": department,
                            "totalPositions": positions,
                            "targetHireDate": target_date,
                            "daysOpen": days_open,
                            "status": status,
                            "recruiter": recruiter_name,
                            "nextAction": next_action,
                            "sources": sources,
                            "pipeline": pipeline
                        })
                        
                global_metrics = {
                    "activeJobs": len(active_jobs),
                    "applicants": total_applications_count,
                    "interviews": {
                        "total": interviews_completed + interviews_cancelled + interviews_pending,
                        "completed": interviews_completed,
                        "cancelled": interviews_cancelled,
                        "pending": interviews_pending
                    },
                    "submissions": submissions_count,
                    "offers": {
                        "total": offers_accepted + offers_declined + offers_pending,
                        "accepted": offers_accepted,
                        "declined": offers_declined,
                        "pending": offers_pending
                    },
                    "hires": global_hires + interview_hires
                }
                
                with ZohoCache.lock:
                    ZohoCache.data = {
                        "status": "live",
                        "globalMetrics": global_metrics,
                        "jobs": mapped_jobs
                    }
                    ZohoCache.last_updated = time.time()
                sys.stdout.write("Zoho cache updated successfully.\n")
            except Exception as e:
                sys.stderr.write(f"Zoho cache update failed: {str(e)}\n")
            finally:
                with ZohoCache.lock:
                    ZohoCache.is_updating = False
                    
        if background:
            t = threading.Thread(target=run_update)
            t.daemon = True
            t.start()
        else:
            run_update()

    def serve_fallback_data(self, message, status="demo"):
        sys.stderr.write(f"Serving fallback data: {message}\n")
        
        # Read standard data.js fallback mock data
        fallback_file = os.path.join(BASE_DIR, "data.js")
        mock_jobs = []
        
        # Quick parse of data.js to get jobOpeningsData
        try:
            with open(fallback_file, 'r') as f:
                content = f.read()
                # Find start of array and end of array
                start_idx = content.find("const jobOpeningsData = [")
                if start_idx != -1:
                    start_idx = content.find("[", start_idx)
                    # Simple extraction
                    bracket_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(content)):
                        if content[i] == '[':
                            bracket_count += 1
                        elif content[i] == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_idx = i
                                break
                    js_array = content[start_idx:end_idx+1]
                    
                    # Clean JS code to be valid JSON by removing comments and parsing safely
                    # For simplicity, we write a hardcoded copy of mock database or parse simply.
                    # Since data structure in data.js matches config, we can hardcode the mock list here as absolute fallback.
        except:
            pass

        mock_jobs = [
          {
            "id": "JOB-001",
            "companyName": "Apex Global Tech",
            "jobTitle": "Senior Frontend Engineer (React)",
            "department": "Engineering",
            "totalPositions": 3,
            "targetHireDate": "2026-07-20",
            "daysOpen": 18,
            "status": "On Track",
            "recruiter": "Sarah Jenkins",
            "nextAction": "Schedule final technical round for finalist candidate by EOD.",
            "sources": { "naukri": 45, "linkedin": 60, "referral": 15, "website": 10 },
            "pipeline": { "screening": 42, "interview": 18, "offered": 2, "rejected": 65, "hired": 3 }
          },
          {
            "id": "JOB-002",
            "companyName": "Nexus Software Systems",
            "jobTitle": "Technical Product Manager",
            "department": "Product Management",
            "totalPositions": 1,
            "targetHireDate": "2026-07-05",
            "daysOpen": 28,
            "status": "Delayed",
            "recruiter": "David Smith",
            "nextAction": "Follow up with VP of Product on compensation review.",
            "sources": { "naukri": 20, "linkedin": 35, "referral": 5, "website": 8 },
            "pipeline": { "screening": 22, "interview": 8, "offered": 1, "rejected": 36, "hired": 1 }
          },
          {
            "id": "JOB-003",
            "companyName": "Apex Global Tech",
            "jobTitle": "Senior Data Scientist (GenAI & LLMs)",
            "department": "Data & AI",
            "totalPositions": 2,
            "targetHireDate": "2026-08-10",
            "daysOpen": 8,
            "status": "On Track",
            "recruiter": "Sarah Jenkins",
            "nextAction": "Source candidate shortlists specializing in PyTorch and transformer models.",
            "sources": { "naukri": 12, "linkedin": 25, "referral": 3, "website": 2 },
            "pipeline": { "screening": 15, "interview": 4, "offered": 0, "rejected": 21, "hired": 2 }
          },
          {
            "id": "JOB-004",
            "companyName": "CloudScale Dynamics",
            "jobTitle": "Lead DevOps Engineer (Kubernetes & AWS)",
            "department": "Infrastructure",
            "totalPositions": 2,
            "targetHireDate": "2026-06-15",
            "daysOpen": 45,
            "status": "Delayed",
            "recruiter": "Michael Green",
            "nextAction": "Review JD requirements with Engineering Director; sourcing is currently stalled.",
            "sources": { "naukri": 62, "linkedin": 85, "referral": 2, "website": 6 },
            "pipeline": { "screening": 85, "interview": 12, "offered": 0, "rejected": 58, "hired": 0 }
          },
          {
            "id": "JOB-005",
            "companyName": "Nexus Software Systems",
            "jobTitle": "HR People Operations Lead",
            "department": "Human Resources",
            "totalPositions": 1,
            "targetHireDate": "2026-07-25",
            "daysOpen": 12,
            "status": "On Track",
            "recruiter": "Emma Watson",
            "nextAction": "Conduct initial HR phone screenings for top 5 applicants.",
            "sources": { "naukri": 15, "linkedin": 18, "referral": 4, "website": 11 },
            "pipeline": { "screening": 14, "interview": 6, "offered": 0, "rejected": 28, "hired": 0 }
          },
          {
            "id": "JOB-006",
            "companyName": "Vanguard Financial Technologies",
            "jobTitle": "Enterprise Account Executive",
            "department": "Sales",
            "totalPositions": 2,
            "targetHireDate": "2026-07-15",
            "daysOpen": 15,
            "status": "On Track",
            "recruiter": "Emma Watson",
            "nextAction": "Send formal offer letter to candidate.",
            "sources": { "naukri": 28, "linkedin": 42, "referral": 10, "website": 5 },
            "pipeline": { "screening": 30, "interview": 15, "offered": 1, "rejected": 37, "hired": 2 }
          }
        ]

        response_data = {
            "status": status,
            "message": message,
            "globalMetrics": {
                "activeJobs": 39,
                "applicants": 2207,
                "interviews": {
                    "total": 124,
                    "completed": 11,
                    "cancelled": 42,
                    "pending": 71
                },
                "submissions": 0,
                "offers": {
                    "total": 132,
                    "accepted": 75,
                    "declined": 50,
                    "pending": 7
                },
                "hires": 78
            },
            "jobs": mock_jobs
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def serve_static_file(self, path):
        # Resolve request path to local path
        if path == "/" or not path:
            path = "/index.html"
            
        rel_path = path.lstrip("/\\")
        local_path = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(local_path) and os.path.isfile(local_path):
            self.send_response(200)
            
            # Content Type Mapping
            mime_type, _ = mimetypes.guess_type(local_path)
            if mime_type:
                self.send_header('Content-Type', mime_type)
                
            self.end_headers()
            with open(local_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def serve_error(self, message):
        self.send_response(500)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
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
        self.wfile.write(error_html.encode('utf-8'))

# Run server
class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

# Export handler for Vercel serverless runtime
handler = OAuthProxyHandler

if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), OAuthProxyHandler)
    print(f"Starting server on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Server stopped.")
