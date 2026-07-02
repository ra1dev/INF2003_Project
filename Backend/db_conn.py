import psycopg2
from flask import g


def get_db():
    """Return a PostgreSQL connection stored for the current request context."""
    if "db" not in g:
        g.db = psycopg2.connect(
            host="localhost",
            dbname="epl_db_2",
            user="postgres",
            password="Password",
            port=5432
        )
    return g.db


def close_db(e=None):
    """Close the request-scoped database connection when the request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Register the teardown hook so each request closes its database connection."""
    app.teardown_appcontext(close_db)