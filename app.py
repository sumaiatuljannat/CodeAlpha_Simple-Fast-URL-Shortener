import os
import random
import string
import sqlite3
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, abort, flash, url_for

# Initialize Flask application
app = Flask(__name__)
# Secret key required for Flask session/flash messages
app.secret_key = "url-shortener-secret-key-change-in-prod"

# Database file location in the same directory as app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    row_factory = sqlite3.Row allows accessing columns by name like a dictionary.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the database by executing schema.sql if the table doesn't exist.
    """
    schema_file = os.path.join(BASE_DIR, "schema.sql")
    with get_db_connection() as conn:
        with open(schema_file, mode="r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()


def generate_short_code(length=6):
    """
    Generates a random alphanumeric short code of specified length (default 6).
    Example characters: a-z, A-Z, 0-9.
    """
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


def is_valid_url(url):
    """
    Validates that a URL is non-empty, starts with http:// or https://,
    and has a valid network location (domain).
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    
    parsed = urlparse(url)
    return bool(parsed.netloc)


@app.route("/", methods=["GET"])
def index():
    """
    Home page route. Displays the URL shortener input form.
    """
    return render_template("index.html")


@app.route("/shorten", methods=["POST"])
def shorten_url():
    """
    Processes form submission to create a shortened URL.
    Validates original URL, generates a unique code, and saves to database.
    """
    original_url = request.form.get("original_url", "").strip()

    # 1. Validation: check if URL is empty or missing protocol
    if not original_url:
        flash("Please enter a URL to shorten.", "error")
        return redirect(url_for("index"))

    if not is_valid_url(original_url):
        flash("Invalid URL! URL must start with http:// or https:// and include a valid domain.", "error")
        return redirect(url_for("index"))

    conn = get_db_connection()

    # 2. Check if the original URL already exists in database (optional reuse)
    existing = conn.execute(
        "SELECT short_code FROM urls WHERE original_url = ?",
        (original_url,)
    ).fetchone()

    if existing:
        short_code = existing["short_code"]
        conn.close()
    else:
        # 3. Generate a unique short code
        while True:
            code_candidate = generate_short_code(length=6)
            # Check if this code already exists to prevent collisions
            found = conn.execute(
                "SELECT id FROM urls WHERE short_code = ?",
                (code_candidate,)
            ).fetchone()
            if not found:
                short_code = code_candidate
                break

        # 4. Insert into SQLite using parameterized query to prevent SQL Injection
        conn.execute(
            "INSERT INTO urls (original_url, short_code) VALUES (?, ?)",
            (original_url, short_code)
        )
        conn.commit()
        conn.close()

    # Build full short URL (e.g. http://localhost:5000/abc123)
    short_url = request.host_url + short_code

    return render_template(
        "index.html",
        short_url=short_url,
        short_code=short_code,
        original_url=original_url
    )


@app.route("/<short_code>", methods=["GET"])
def redirect_to_url(short_code):
    """
    Redirects the user to the original URL associated with the short_code.
    Increments click_count by 1 upon each visit.
    """
    conn = get_db_connection()
    url_data = conn.execute(
        "SELECT id, original_url FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()

    if url_data is None:
        conn.close()
        # Non-existing short code -> render 404 page
        abort(404)

    # Increment click count using parameterized query
    conn.execute(
        "UPDATE urls SET click_count = click_count + 1 WHERE id = ?",
        (url_data["id"],)
    )
    conn.commit()
    conn.close()

    # 302 temporary redirect to original destination URL
    return redirect(url_data["original_url"])


@app.route("/stats/<short_code>", methods=["GET"])
def url_stats(short_code):
    """
    Displays click analytics and details for a given short code.
    """
    conn = get_db_connection()
    url_data = conn.execute(
        "SELECT original_url, short_code, created_at, click_count FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    conn.close()

    if url_data is None:
        abort(404)

    short_url = request.host_url + short_code

    return render_template(
        "stats.html",
        url_data=url_data,
        short_url=short_url
    )


@app.errorhandler(404)
def page_not_found(e):
    """
    Custom 404 Not Found error handler.
    """
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """
    Custom 500 Internal Server Error handler.
    """
    return render_template("error.html", error_message="An unexpected server error occurred."), 500


if __name__ == "__main__":
    # Initialize the database on first run
    init_db()
    print("Database initialized successfully.")
    print("Starting Flask development server on http://127.0.0.1:5000 ...")
    # Run server locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
