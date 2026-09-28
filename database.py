"""
Database connection, initialization, and migration helpers for LinkSnap.
"""
import os
import sqlite3
from typing import Generator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes and returns an active SQLite connection configured with:
    - row_factory = sqlite3.Row for dictionary-like column access
    - foreign_keys = ON to enforce referential integrity and cascade deletes
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Initializes the database schema and performs any necessary migrations.
    """
    with get_db_connection() as conn:
        with open(SCHEMA_PATH, mode="r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Check if legacy 'urls' table exists from earlier prototype
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='urls';"
        )
        has_legacy = cursor.fetchone() is not None

        if has_legacy:
            # Check if links table is empty
            count = conn.execute("SELECT COUNT(*) AS c FROM links;").fetchone()["c"]
            if count == 0:
                # Migrate records from legacy 'urls' table
                legacy_rows = conn.execute(
                    "SELECT original_url, short_code, created_at, click_count FROM urls;"
                ).fetchall()

                for row in legacy_rows:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO links (original_url, short_code, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (row["original_url"], row["short_code"], row["created_at"])
                    )
                    link_id = cursor.lastrowid
                    if link_id and row["click_count"] > 0:
                        # Insert placeholder clicks to preserve click count
                        for _ in range(row["click_count"]):
                            conn.execute(
                                """
                                INSERT INTO clicks (link_id, clicked_at, referrer, device_type)
                                VALUES (?, ?, 'Legacy', 'Desktop')
                                """,
                                (link_id, row["created_at"])
                            )

            # Drop old table after successful migration
            conn.execute("DROP TABLE IF EXISTS urls;")

        conn.commit()
