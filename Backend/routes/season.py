from flask import Blueprint

from Backend.repositories.season_repository import season_recap as render_season_recap
from Backend.repositories.season_repository import season_table as render_season_table

season_bp = Blueprint("season", __name__)


@season_bp.route("/season-recap")
def season_recap():
    return render_season_recap()


@season_bp.route("/season-table")
def season_table():
    return render_season_table()
