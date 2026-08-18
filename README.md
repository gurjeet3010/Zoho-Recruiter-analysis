# ⚡ TalentPulse — Executive Recruitment Command Center

A modern, high-fidelity real-time executive dashboard for monitoring corporate talent acquisition pipelines, sourcing channel conversion rates, recruiter throughput, and active job requisitions.

Designed as an executive single-pane-of-glass interface with live **Zoho Recruit OAuth 2.0 integration** and offline demo mode fallback.

---

## 🌟 Key Features

* **📊 Executive KPI Overview**: Real-time snapshot of active job requisitions, total applicants, scheduled/completed/cancelled interviews, candidate submissions, offers extended/accepted, and total hires.
* **🎯 Interactive Aggregate Hiring Funnel**: Chart.js-powered visual stage conversion tracking (*Screening ➔ Technical Interview ➔ Offer ➔ Hired*).
* **🌐 Sourcing Channel Attribution**: Granular source split analysis (*LinkedIn, Naukri, Employee Referrals, Corporate Career Portal*).
* **📋 Active Job Requisition Drill-Down**: Interactive data grid with search, multi-criteria filtering (*Company, Hiring Status*), and column sorting.
* **🔍 Deep Job Detail Modal**: Comprehensive candidate breakdown, days open, target hire dates, and next recruiter action items.
* **🔐 Zoho Recruit OAuth 2.0 & Demo Mode**: Multi-threaded backend server with secure token refresh cycle, local SQLite/file cache, and instant offline mock mode.
* **🎨 Premium Glassmorphic UI**: Custom Vanilla CSS design system with subtle gradients, typography (Inter & Outfit), responsive tables, and dark mode palette.

---

## 🛠️ Architecture & Tech Stack

```
[ Frontend: HTML5 / Vanilla CSS / JavaScript ]
           │
           │  (REST API calls: /api/jobs, /api/status)
           ▼
[ Backend Proxy: Python ThreadingHTTPServer (Zero External Dependencies) ]
           │
           │  (OAuth 2.0 Token Exchange & Refresh)
           ▼
[ Zoho Recruit REST API v2 / Mock Data Cache ]
```

* **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS (Custom Design System), Chart.js, FontAwesome Icons.
* **Backend**: Python 3 standard library (`http.server`, `socketserver`, `urllib`, `threading`, `json`).
* **Integration**: Zoho Recruit API v2 (Job Openings, Candidates, Interviews, Offers).

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/<YOUR_USERNAME>/talentpulse-recruiter-dashboard.git
cd talentpulse-recruiter-dashboard
```

### 2. Run the Server
No `pip install` or external package installation required! Simply run:

```bash
# Option A: Windows Batch Launcher
run.bat

# Option B: Direct Python
python server.py
```

### 3. Open in Browser
Visit **[http://localhost:8123](http://localhost:8123)** in your browser.

---

## ⚙️ Optional Zoho Recruit API Configuration

To connect to a live Zoho Recruit account instead of demo mode:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Create an OAuth client in the [Zoho Developer Console](https://api-console.zoho.com/):
   * **Client Type**: Server-based Applications
   * **Authorized Redirect URI**: `http://localhost:8123/oauth/callback`
3. Add your `ZOHO_CLIENT_ID` and `ZOHO_CLIENT_SECRET` in `.env`.
4. Click **"Connect Zoho Recruit"** from the top header to authorize.

---

## 📄 License
This project is licensed under the MIT License - open for personal and commercial portfolio demonstrations.
