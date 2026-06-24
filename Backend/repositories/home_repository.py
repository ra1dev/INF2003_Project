from flask import render_template

from Backend.db_conn import get_db


def home():
    return render_template("index.html", title="Home")


def tables():
    return render_template("tables.html", title="Database Tables")


def db_test():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM player LIMIT 10;")
    players = cur.fetchall()

    cur.close()

    return str(players)
