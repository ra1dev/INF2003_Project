# Route handlers for the landing and utility pages.
from flask import Blueprint

from Backend.repositories.home_repository import db_test as render_db_test
from Backend.repositories.home_repository import home as render_home
from Backend.repositories.home_repository import tables as render_tables

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    return render_home()


@home_bp.route("/tables")
def tables():
    return render_tables()


@home_bp.route("/db")
def db_test():
    return render_db_test()
