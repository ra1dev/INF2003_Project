from flask import render_template

from Backend.db_conn import get_db


def home():
    """Render the main landing page for the application."""
    return render_template("index.html", title="Home")


def tables():
    """Render the page that lists the available database tables."""
    return render_template("tables.html", title="Database Tables")


def db_test():
    """Return a small sample of data to validate the relational database connection."""
    conn = get_db()
    cur = conn.cursor()

    # Fetch a small sample so the route can verify the connection quickly.
    cur.execute("SELECT * FROM player LIMIT 10;")
    players = cur.fetchall()

    cur.close()

    return str(players)
