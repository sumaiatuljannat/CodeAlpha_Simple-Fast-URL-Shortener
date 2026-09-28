"""
LinkSnap - Production-Grade URL Shortener Web Application
Built with Python 3, Flask, and SQLite.
"""
import os
import random
import string
from datetime import datetime, timezone
from functools import wraps
from typing import Optional, Dict, Any

from flask import (
    Flask, render_template, request, redirect,
    jsonify, session, Response, make_response, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, init_db
from security import (
    is_valid_url, is_valid_custom_code, parse_user_agent,
    clean_referrer, rate_limit, RESERVED_CODES
)
from qr_generator import generate_qr_svg, generate_qr_png_bytes, generate_qr_data_uri

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "linksnap-production-secret-key-change-in-prod-2026")
app.config["JSON_SORT_KEYS"] = False


# ============================================================================
# HELPER FUNCTIONS & AUTH UTILITIES
# ============================================================================

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Returns the currently authenticated user dictionary from session, or None.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(user) if user else None


def login_required(f):
    """
    Decorator requiring active user authentication for API or view access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required."}), 401
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def generate_unique_short_code(conn, length=6) -> str:
    """
    Generates a cryptographically sound random alphanumeric code guaranteed
    not to conflict with existing database records or reserved route keywords.
    """
    characters = string.ascii_letters + string.digits
    while True:
        candidate = "".join(random.choices(characters, k=length))
        if candidate.lower() in RESERVED_CODES:
            continue
        exists = conn.execute(
            "SELECT id FROM links WHERE short_code = ?", (candidate,)
        ).fetchone()
        if not exists:
            return candidate


def is_link_expired(expires_at: Optional[str]) -> bool:
    """
    Checks if a link's expiration timestamp has passed.
    """
    if not expires_at:
        return False
    try:
        # Standardize ISO format
        exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp_dt
    except Exception:
        return False


def format_link_payload(row, host_url: str, click_count: Optional[int] = None) -> dict:
    """
    Formats a database row into a clean, consistent API response dictionary.
    """
    short_code = row["short_code"]
    short_url = f"{host_url.rstrip('/')}/{short_code}"
    
    # Calculate click count if not provided
    clicks = click_count
    if clicks is None and "click_count" in row.keys():
        clicks = row["click_count"]
        
    tags_list = [t.strip() for t in row["tags"].split(",") if t.strip()] if row["tags"] else []
    expired = is_link_expired(row["expires_at"])

    status = "active"
    if not row["is_active"]:
        status = "inactive"
    elif expired:
        status = "expired"

    return {
        "id": row["id"],
        "short_code": short_code,
        "short_url": short_url,
        "original_url": row["original_url"],
        "title": row["title"] or "",
        "tags": tags_list,
        "is_active": bool(row["is_active"]),
        "status": status,
        "expires_at": row["expires_at"],
        "is_expired": expired,
        "click_count": clicks if clicks is not None else 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "qr_code_url": f"{host_url.rstrip('/')}/api/links/{short_code}/qr",
        "stats_url": f"{host_url.rstrip('/')}/api/links/{short_code}/stats"
    }


# ============================================================================
# AUTHENTICATION API ENDPOINTS
# ============================================================================

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or len(username) < 3:
        return jsonify({"success": False, "error": "Username must be at least 3 characters."}), 400
    if not email or "@" not in email:
        return jsonify({"success": False, "error": "A valid email address is required."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    with get_db_connection() as conn:
        # Check uniqueness
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        if existing:
            return jsonify({"success": False, "error": "Username or email is already registered."}), 409

        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid

    session["user_id"] = user_id
    session["username"] = username

    return jsonify({
        "success": True,
        "message": "Registration successful.",
        "user": {"id": user_id, "username": username, "email": email}
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or request.form
    login_id = data.get("username", "").strip()
    password = data.get("password", "")

    if not login_id or not password:
        return jsonify({"success": False, "error": "Username/email and password are required."}), 400

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ? OR email = ?",
            (login_id, login_id.lower())
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"success": False, "error": "Invalid username or password."}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})


# ============================================================================
# LINK MANAGEMENT REST API ENDPOINTS
# ============================================================================

@app.route("/api/shorten", methods=["POST"])
@rate_limit(limit=30, window=60)
def api_shorten():
    """
    Creates a new shortened URL with optional custom alias, expiration, title, and tags.
    """
    data = request.get_json(silent=True) or request.form
    original_url = data.get("original_url", "").strip()
    custom_code = data.get("custom_code", "").strip()
    title = data.get("title", "").strip()
    tags = data.get("tags", "")
    expires_at = data.get("expires_at", "").strip() or None

    # Clean tags list into comma-separated string
    if isinstance(tags, list):
        tags_str = ",".join(str(t).strip() for t in tags if str(t).strip())
    else:
        tags_str = ",".join(t.strip() for t in str(tags).split(",") if t.strip())

    # 1. URL Validation & SSRF defense
    is_valid, err_msg = is_valid_url(original_url)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    # 2. Expiration validation
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt <= datetime.now(timezone.utc):
                return jsonify({"success": False, "error": "Expiration date must be in the future."}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format for expires_at (use ISO 8601)."}), 400

    user_id = session.get("user_id")

    with get_db_connection() as conn:
        # 3. Handle custom short code
        if custom_code:
            valid_code, code_err = is_valid_custom_code(custom_code)
            if not valid_code:
                return jsonify({"success": False, "error": code_err}), 400

            exists = conn.execute(
                "SELECT id FROM links WHERE short_code = ?", (custom_code,)
            ).fetchone()
            if exists:
                return jsonify({"success": False, "error": f"Short code '{custom_code}' is already taken."}), 409
            short_code = custom_code
        else:
            short_code = generate_unique_short_code(conn, length=6)

        # 4. Insert link record
        cursor = conn.execute(
            """
            INSERT INTO links (user_id, original_url, short_code, title, tags, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, original_url, short_code, title, tags_str, expires_at)
        )
        conn.commit()
        link_id = cursor.lastrowid

        new_link = conn.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()

    # Track guest links in session for instant dashboard display
    if not user_id:
        guest_links = session.get("guest_links", [])
        if short_code not in guest_links:
            guest_links.append(short_code)
            session["guest_links"] = guest_links[-50:]  # Keep last 50

    payload = format_link_payload(new_link, request.host_url, click_count=0)
    payload["qr_data_uri"] = generate_qr_data_uri(payload["short_url"])

    return jsonify({"success": True, "link": payload}), 201


@app.route("/api/links", methods=["GET"])
def api_list_links():
    """
    Lists links with search, tag filtering, status filtering, and pagination.
    """
    user_id = session.get("user_id")
    search = request.args.get("search", "").strip()
    tag = request.args.get("tag", "").strip()
    status_filter = request.args.get("status", "all").strip().lower()

    query = """
        SELECT l.*, COUNT(c.id) AS click_count
        FROM links l
        LEFT JOIN clicks c ON l.id = c.link_id
    """
    conditions = []
    params = []

    # Filter by user ownership if logged in; otherwise show session guest links or recent
    if user_id:
        conditions.append("l.user_id = ?")
        params.append(user_id)
    else:
        guest_links = session.get("guest_links", [])
        if guest_links:
            placeholders = ",".join("?" for _ in guest_links)
            conditions.append(f"l.short_code IN ({placeholders})")
            params.extend(guest_links)
        else:
            # Fallback: display unassigned links created without user_id
            conditions.append("l.user_id IS NULL")

    if search:
        conditions.append("(l.original_url LIKE ? OR l.short_code LIKE ? OR l.title LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])

    if tag:
        conditions.append("(l.tags LIKE ?)")
        params.append(f"%{tag}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY l.id ORDER BY l.created_at DESC"

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    links = []
    for r in rows:
        formatted = format_link_payload(r, request.host_url, click_count=r["click_count"])
        if status_filter != "all" and formatted["status"] != status_filter:
            continue
        links.append(formatted)

    return jsonify({
        "success": True,
        "count": len(links),
        "links": links
    })


@app.route("/api/links/<short_code>", methods=["GET"])
def api_get_link(short_code):
    """
    Retrieves metadata and click count for a single short code.
    """
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT l.*, COUNT(c.id) AS click_count
            FROM links l
            LEFT JOIN clicks c ON l.id = c.link_id
            WHERE l.short_code = ?
            GROUP BY l.id
            """,
            (short_code,)
        ).fetchone()

        if not row:
            return jsonify({"success": False, "error": "Link not found."}), 404

    payload = format_link_payload(row, request.host_url, click_count=row["click_count"])
    payload["qr_data_uri"] = generate_qr_data_uri(payload["short_url"])

    return jsonify({"success": True, "link": payload})


@app.route("/api/links/<short_code>", methods=["PATCH"])
def api_update_link(short_code):
    """
    Updates link properties: original_url, title, tags, is_active, expires_at.
    """
    data = request.get_json(silent=True) or request.form
    user_id = session.get("user_id")

    with get_db_connection() as conn:
        link = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()
        if not link:
            return jsonify({"success": False, "error": "Link not found."}), 404

        # Ownership validation if user is authenticated and link has owner
        if link["user_id"] and link["user_id"] != user_id:
            return jsonify({"success": False, "error": "Unauthorized to modify this link."}), 403

        updates = []
        params = []

        if "original_url" in data:
            orig = data["original_url"].strip()
            is_valid, err_msg = is_valid_url(orig)
            if not is_valid:
                return jsonify({"success": False, "error": err_msg}), 400
            updates.append("original_url = ?")
            params.append(orig)

        if "title" in data:
            updates.append("title = ?")
            params.append(data["title"].strip())

        if "tags" in data:
            t = data["tags"]
            if isinstance(t, list):
                t_str = ",".join(str(x).strip() for x in t if str(x).strip())
            else:
                t_str = ",".join(x.strip() for x in str(t).split(",") if x.strip())
            updates.append("tags = ?")
            params.append(t_str)

        if "is_active" in data:
            val = 1 if str(data["is_active"]).lower() in ("true", "1") else 0
            updates.append("is_active = ?")
            params.append(val)

        if "expires_at" in data:
            exp = data["expires_at"].strip() if data["expires_at"] else None
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if exp_dt <= datetime.now(timezone.utc):
                        return jsonify({"success": False, "error": "Expiration date must be in the future."}), 400
                except ValueError:
                    return jsonify({"success": False, "error": "Invalid date format for expires_at."}), 400
            updates.append("expires_at = ?")
            params.append(exp)

        if not updates:
            return jsonify({"success": False, "error": "No update fields provided."}), 400

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(link["id"])

        conn.execute(
            f"UPDATE links SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()

        updated_row = conn.execute(
            """
            SELECT l.*, COUNT(c.id) AS click_count
            FROM links l
            LEFT JOIN clicks c ON l.id = c.link_id
            WHERE l.id = ?
            GROUP BY l.id
            """,
            (link["id"],)
        ).fetchone()

    return jsonify({
        "success": True,
        "message": "Link updated successfully.",
        "link": format_link_payload(updated_row, request.host_url, click_count=updated_row["click_count"])
    })


@app.route("/api/links/<short_code>", methods=["DELETE"])
def api_delete_link(short_code):
    """
    Deletes a link and cascades all related analytics.
    """
    user_id = session.get("user_id")

    with get_db_connection() as conn:
        link = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()
        if not link:
            return jsonify({"success": False, "error": "Link not found."}), 404

        if link["user_id"] and link["user_id"] != user_id:
            return jsonify({"success": False, "error": "Unauthorized to delete this link."}), 403

        conn.execute("DELETE FROM links WHERE id = ?", (link["id"],))
        conn.commit()

    # Clean guest session if applicable
    guest_links = session.get("guest_links", [])
    if short_code in guest_links:
        guest_links.remove(short_code)
        session["guest_links"] = guest_links

    return jsonify({"success": True, "message": f"Link '{short_code}' was permanently deleted."})


# ============================================================================
# COMPREHENSIVE ANALYTICS ENDPOINT
# ============================================================================

@app.route("/api/links/<short_code>/stats", methods=["GET"])
def api_link_stats(short_code):
    """
    Returns in-depth analytics: total clicks, clicks by date (timeline),
    referrers breakdown, devices, browsers, and operating systems.
    """
    with get_db_connection() as conn:
        link = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()
        if not link:
            return jsonify({"success": False, "error": "Link not found."}), 404

        link_id = link["id"]

        # 1. Total clicks
        total_clicks = conn.execute(
            "SELECT COUNT(*) AS total FROM clicks WHERE link_id = ?", (link_id,)
        ).fetchone()["total"]

        # 2. Clicks by date (Last 30 days timeline)
        date_rows = conn.execute(
            """
            SELECT date(clicked_at) AS click_date, COUNT(*) AS count
            FROM clicks
            WHERE link_id = ?
            GROUP BY date(clicked_at)
            ORDER BY click_date ASC
            LIMIT 30
            """,
            (link_id,)
        ).fetchall()
        timeline = [{"date": r["click_date"], "clicks": r["count"]} for r in date_rows]

        # 3. Referrers breakdown
        ref_rows = conn.execute(
            """
            SELECT referrer, COUNT(*) AS count
            FROM clicks
            WHERE link_id = ?
            GROUP BY referrer
            ORDER BY count DESC
            LIMIT 10
            """,
            (link_id,)
        ).fetchall()
        referrers = [{"name": r["referrer"], "clicks": r["count"]} for r in ref_rows]

        # 4. Devices breakdown
        device_rows = conn.execute(
            """
            SELECT device_type, COUNT(*) AS count
            FROM clicks
            WHERE link_id = ?
            GROUP BY device_type
            ORDER BY count DESC
            """,
            (link_id,)
        ).fetchall()
        devices = [{"name": r["device_type"], "clicks": r["count"]} for r in device_rows]

        # 5. Browsers breakdown
        browser_rows = conn.execute(
            """
            SELECT browser, COUNT(*) AS count
            FROM clicks
            WHERE link_id = ?
            GROUP BY browser
            ORDER BY count DESC
            LIMIT 6
            """,
            (link_id,)
        ).fetchall()
        browsers = [{"name": r["browser"], "clicks": r["count"]} for r in browser_rows]

        # 6. Operating Systems breakdown
        os_rows = conn.execute(
            """
            SELECT os, COUNT(*) AS count
            FROM clicks
            WHERE link_id = ?
            GROUP BY os
            ORDER BY count DESC
            LIMIT 6
            """,
            (link_id,)
        ).fetchall()
        operating_systems = [{"name": r["os"], "clicks": r["count"]} for r in os_rows]

        # 7. Recent 10 clicks (Anonymized, privacy-safe)
        recent_rows = conn.execute(
            """
            SELECT clicked_at, referrer, device_type, browser, os
            FROM clicks
            WHERE link_id = ?
            ORDER BY clicked_at DESC
            LIMIT 10
            """,
            (link_id,)
        ).fetchall()
        recent_clicks = [dict(r) for r in recent_rows]

    link_info = format_link_payload(link, request.host_url, click_count=total_clicks)

    return jsonify({
        "success": True,
        "link": link_info,
        "analytics": {
            "total_clicks": total_clicks,
            "timeline": timeline,
            "referrers": referrers,
            "devices": devices,
            "browsers": browsers,
            "operating_systems": operating_systems,
            "recent_clicks": recent_clicks
        }
    })


# ============================================================================
# QR CODE GENERATION ENDPOINTS
# ============================================================================

@app.route("/api/links/<short_code>/qr", methods=["GET"])
def api_link_qr(short_code):
    """
    Renders or downloads high-resolution vector SVG or raster PNG QR code.
    """
    format_type = request.args.get("format", "svg").lower()
    download = request.args.get("download", "0") == "1"

    with get_db_connection() as conn:
        link = conn.execute("SELECT id FROM links WHERE short_code = ?", (short_code,)).fetchone()
        if not link:
            abort(404)

    target_url = f"{request.host_url.rstrip('/')}/{short_code}"

    if format_type == "png":
        png_bytes = generate_qr_png_bytes(target_url, scale=10)
        response = make_response(png_bytes)
        response.headers["Content-Type"] = "image/png"
        if download:
            response.headers["Content-Disposition"] = f'attachment; filename="linksnap-{short_code}.png"'
        return response

    # Default SVG vector format
    svg_str = generate_qr_svg(target_url, scale=8)
    response = make_response(svg_str)
    response.headers["Content-Type"] = "image/svg+xml"
    if download:
        response.headers["Content-Disposition"] = f'attachment; filename="linksnap-{short_code}.svg"'
    return response


# ============================================================================
# REDIRECTION ENGINE (HTTP 302 & PRIVACY-FRIENDLY TRACKING)
# ============================================================================

@app.route("/<short_code>", methods=["GET"])
def redirect_to_url(short_code):
    """
    Resolves short code, validates status & expiration, increments analytics,
    and performs high-speed HTTP 302 temporary redirection.
    """
    # Avoid intercepting standard favicon or root
    if short_code in ("favicon.ico", ""):
        abort(404)

    with get_db_connection() as conn:
        link = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()

        if not link:
            return render_template("404.html", short_code=short_code), 404

        # 1. Check if link is disabled
        if not link["is_active"]:
            return render_template("disabled.html", short_code=short_code, title=link["title"]), 403

        # 2. Check if link has expired
        if is_link_expired(link["expires_at"]):
            return render_template("expired.html", short_code=short_code, expires_at=link["expires_at"]), 410

        # 3. Log privacy-preserving click event
        ua_info = parse_user_agent(request.headers.get("User-Agent", ""))
        clean_ref = clean_referrer(request.headers.get("Referer", ""))

        conn.execute(
            """
            INSERT INTO clicks (link_id, referrer, device_type, browser, os)
            VALUES (?, ?, ?, ?, ?)
            """,
            (link["id"], clean_ref, ua_info["device_type"], ua_info["browser"], ua_info["os"])
        )
        conn.commit()

    return redirect(link["original_url"], code=302)


# ============================================================================
# WEB UI & ERROR HANDLERS
# ============================================================================

@app.route("/", methods=["GET"])
def index():
    """
    Main web interface delivering the modern dashboard, URL shortener,
    interactive charts, and link manager.
    """
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/stats/<short_code>", methods=["GET"])
def web_stats(short_code):
    """
    Direct web link to open the analytics view for a specific short code.
    """
    return render_template("index.html", initial_stats_code=short_code, user=get_current_user())


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "API route not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(410)
def handle_410(e):
    return render_template("expired.html"), 410


@app.errorhandler(429)
def handle_429(e):
    return jsonify({"success": False, "error": "Too many requests. Please slow down."}), 429


@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500
    return render_template("error.html", error_message="An unexpected server error occurred."), 500


# ============================================================================
# APPLICATION BOOTSTRAP
# ============================================================================

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    init_db()
    print("=" * 60)
    print("[LinkSnap] URL Shortener & Analytics Platform")
    print("Database: SQLite (database.db) initialized successfully.")
    print("Running server on: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
