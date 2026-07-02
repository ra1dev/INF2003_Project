# Route handlers for team listings, detail views, and comparisons.
from flask import Blueprint

from Backend.repositories.teams_repository import team_comparison as render_team_comparison
from Backend.repositories.teams_repository import team_detail as render_team_detail
from Backend.repositories.teams_repository import teams as render_teams

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/teams")
def teams():
    return render_teams()


@teams_bp.route("/team-comparison")
def team_comparison():
    return render_team_comparison()


@teams_bp.route("/team/<int:team_id>")
def team_detail(team_id):
    return render_team_detail(team_id)
