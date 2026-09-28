# ⚡ LinkSnap - Enterprise URL Shortener & Analytics Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![SQLite3](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A complete, production-grade URL Shortener and Link Management web application built with **Python 3**, **Flask**, and **SQLite**. Designed for personal links, digital marketing campaigns, events, QR code distribution, and privacy-friendly visitor analytics.

---

## 🌟 Key Features

### 🔗 Core URL Shortening
- **Automated Code Generation:** Fast, collision-resistant 6-character alphanumeric slugs ($62^6 \approx 56.8 \text{ billion}$ unique combinations).
- **Custom Slugs:** Support for vanity aliases (e.g. `/my-product`, `/launch-2026`).
- **High-Speed Redirection:** HTTP 302 temporary redirects ensure visits always route through the analytics engine without stale browser caches.
- **Strict Input Validation & SSRF Defense:** Accepts only valid `http://` and `https://` URLs; blocks dangerous schemes (`javascript:`, `file:`, `data:`) and private/loopback IP ranges (`localhost`, `127.0.0.1`, RFC1918 `10.x`, `192.168.x`).
- **System Keyword Protection:** Blocks reserved routes (`api`, `static`, `login`, `dashboard`, `stats`, etc.).

### 📊 Real-Time Analytics & Privacy
- **Zero Raw IP Logging:** Complete compliance with privacy regulations; raw visitor IP addresses are never persisted.
- **Granular Metrics:**
  - Total click volume and 30-day time-series timeline.
  - Top referrers (Direct, Google, X/Twitter, LinkedIn, GitHub, etc.).
  - Device classification (Desktop, Mobile, Tablet, Bot).
  - Operating system and browser distribution.
  - Chronological anonymized visit logs.
- **Interactive Visualizations:** Embedded Chart.js charts (line charts, doughnut charts, and bar graphs).

### 🛠️ Production Link Management
- **Lifecycle Control:** Toggle links between **Active** and **Inactive** at any time.
- **Automatic Expiration (TTL):** Set custom expiration dates & times; expired links cleanly return HTTP 410 Gone.
- **Campaign Tags:** Categorize links with tags (e.g. `marketing`, `newsletter`) for instant filtering.
- **Integrated QR Codes:** High-resolution vector SVG and raster PNG QR codes generated on-the-fly for every link, with direct one-click download buttons.

### 🔐 Security & Multi-Tenant Authentication
- **Dual Access Modes:**
  - **Guest Mode:** Instant link creation without an account (links persisted to client session).
  - **Authenticated Mode:** Personal dashboard with isolated link ownership and protected modification/deletion permissions.
- **Password Security:** Scrypt / PBKDF2 with SHA-256 salted password hashing via Werkzeug.
- **Sliding-Window Rate Limiting:** Built-in rate limiting per client IP to prevent link creation abuse and denial of service.
- **Parameterized Queries:** 100% protection against SQL Injection attacks.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3, Flask 3.1, Werkzeug |
| **Database** | SQLite3 with Foreign Key Cascades & Indexes |
| **QR Engine** | Segno (Pure Python vector SVG & raster PNG) |
| **Frontend** | Semantic HTML5, Custom CSS3, Vanilla ES6 JavaScript |
| **Data Viz** | Chart.js 4.4 (via CDN) |
| **Testing** | Pytest 9.1 |
| **Production WSGI** | Gunicorn |

---

## 📁 Project Structure

```text
url-shortener/
├── app.py                     # Main Flask application & route controllers
├── database.py                # Database connection, pooling, and schema migration
├── security.py                # SSRF validation, rate limiting, and User-Agent parser
├── qr_generator.py            # SVG and PNG QR code generation engine
├── schema.sql                 # SQLite relational schema definition
├── requirements.txt           # Python package dependencies
├── README.md                  # Comprehensive project documentation
│
├── templates/                 # Jinja2 HTML templates
│   ├── index.html             # Main dashboard, shortener, and modals UI
│   ├── 404.html               # Custom 404 Not Found error page
│   ├── expired.html           # Custom 410 Link Expired page
│   ├── disabled.html          # Custom 403 Link Inactive page
│   └── error.html             # Generic server error page
│
├── static/                    # Frontend assets
│   ├── style.css              # Modern SaaS design system & responsive layout
│   └── script.js              # REST API client, Chart.js graphs, clipboard, modals
│
└── tests/                     # Automated test suite
    ├── conftest.py            # Isolated temporary SQLite test fixture
    ├── test_shortener.py      # Creation, custom codes, validation & SSRF
    ├── test_redirect.py       # Redirection, click tracking, 403, 404, 410
    ├── test_api.py            # REST API CRUD operations & QR code endpoints
    ├── test_auth.py           # Registration, login, sessions & ownership
    └── test_security_and_limits.py # Rate limiter & date validation tests
```

---

## 🚀 Quickstart & Setup on Windows / Linux

### 1. Open Project Directory
```powershell
cd url-shortener
```

### 2. Activate Virtual Environment
**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```
*(Or Command Prompt `cmd.exe`: `.\venv\Scripts\activate.bat`)*

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

The database (`database.db`) initializes automatically on startup.  
Visit the application in your browser at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Running Automated Tests

Run the complete test suite with verbose output:
```bash
python -m pytest -v
```

Expected output:
```text
tests/test_api.py::test_api_list_and_search_links PASSED
tests/test_api.py::test_api_patch_update_link PASSED
tests/test_api.py::test_api_delete_link PASSED
tests/test_api.py::test_api_qr_generation PASSED
tests/test_auth.py::test_user_registration_and_login PASSED
tests/test_auth.py::test_duplicate_user_conflict PASSED
tests/test_redirect.py::test_redirect_success_and_click_tracking PASSED
tests/test_redirect.py::test_redirect_missing_link_404 PASSED
tests/test_redirect.py::test_redirect_disabled_link_403 PASSED
tests/test_redirect.py::test_redirect_expired_link_410 PASSED
tests/test_security_and_limits.py::test_sliding_window_rate_limiter_unit PASSED
tests/test_security_and_limits.py::test_future_expiration_validation PASSED
tests/test_shortener.py::test_shorten_valid_url PASSED
tests/test_shortener.py::test_shorten_custom_code PASSED
tests/test_shortener.py::test_shorten_custom_code_conflict PASSED
tests/test_shortener.py::test_shorten_reserved_keyword PASSED
tests/test_shortener.py::test_shorten_invalid_urls PASSED

============================= 17 passed in 2.11s =============================
```

---

## 📡 REST API Reference

All API requests and responses utilize standard JSON and appropriate HTTP status codes.

### 1. Shorten a URL
- **Endpoint:** `POST /api/shorten`
- **Rate Limit:** 30 requests/minute
- **Request Body:**
```json
{
  "original_url": "https://github.com/torvalds/linux",
  "custom_code": "torvalds-linux",
  "title": "Linux Kernel Source",
  "tags": "kernel, open-source",
  "expires_at": "2026-12-31T23:59:59Z"
}
```
- **Response (`201 Created`):**
```json
{
  "success": true,
  "link": {
    "id": 1,
    "short_code": "torvalds-linux",
    "short_url": "http://127.0.0.1:5000/torvalds-linux",
    "original_url": "https://github.com/torvalds/linux",
    "title": "Linux Kernel Source",
    "tags": ["kernel", "open-source"],
    "is_active": true,
    "status": "active",
    "expires_at": "2026-12-31T23:59:59Z",
    "is_expired": false,
    "click_count": 0,
    "created_at": "2026-09-28 22:00:00",
    "qr_code_url": "http://127.0.0.1:5000/api/links/torvalds-linux/qr",
    "stats_url": "http://127.0.0.1:5000/api/links/torvalds-linux/stats",
    "qr_data_uri": "data:image/svg+xml;charset=utf-8,..."
  }
}
```

### 2. List Links
- **Endpoint:** `GET /api/links`
- **Query Parameters:**
  - `search` (string): Filter by original URL, title, or short code.
  - `tag` (string): Filter by tag.
  - `status` (string): `all`, `active`, `inactive`, or `expired`.
- **Response (`200 OK`):**
```json
{
  "success": true,
  "count": 1,
  "links": [ ... ]
}
```

### 3. Update Link
- **Endpoint:** `PATCH /api/links/<short_code>`
- **Request Body:**
```json
{
  "title": "Updated Title",
  "is_active": false,
  "tags": "marketing, updated"
}
```
- **Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Link updated successfully.",
  "link": { ... }
}
```

### 4. Delete Link
- **Endpoint:** `DELETE /api/links/<short_code>`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Link 'torvalds-linux' was permanently deleted."
}
```

### 5. Detailed Analytics
- **Endpoint:** `GET /api/links/<short_code>/stats`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "link": { ... },
  "analytics": {
    "total_clicks": 42,
    "timeline": [
      { "date": "2026-09-28", "clicks": 42 }
    ],
    "referrers": [
      { "name": "Direct", "clicks": 28 },
      { "name": "X / Twitter", "clicks": 14 }
    ],
    "devices": [
      { "name": "Desktop", "clicks": 30 },
      { "name": "Mobile", "clicks": 12 }
    ],
    "browsers": [
      { "name": "Chrome", "clicks": 25 },
      { "name": "Safari", "clicks": 17 }
    ],
    "operating_systems": [
      { "name": "Windows", "clicks": 20 },
      { "name": "iOS", "clicks": 12 }
    ],
    "recent_clicks": [ ... ]
  }
}
```

### 6. QR Code Endpoint
- **Endpoint:** `GET /api/links/<short_code>/qr`
- **Query Parameters:**
  - `format`: `svg` (default vector) or `png` (raster image).
  - `download`: `1` to trigger direct attachment download.

---

## 🔒 Security & Privacy Implementation

1. **SSRF & Private Network Isolation:** The application strictly disallows internal destinations (`127.0.0.1`, `localhost`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`).
2. **Zero IP Address Storage:** Visitor analytics are derived strictly in-memory from user agents and referrers without logging IP addresses or tracking cookies.
3. **Database Integrity:** Foreign key enforcement (`PRAGMA foreign_keys = ON;`) ensures that deleting a link automatically purges orphaned analytics records.
4. **Rate Limiting:** Sliding-window counter limits rapid POST bursts per client identifier.

---

## 🚢 Production Deployment

For production environments, run behind Gunicorn or Waitress with a reverse proxy (e.g. Nginx):

```bash
# Production WSGI with 4 worker processes
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
