from flask import Blueprint

from Backend.repositories.matches_repository import match_detail as render_match_detail
from Backend.repositories.matches_repository import matches as render_matches
from Backend.repositories.matches_repository import player_match_performance as render_player_match_performance

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/matches")
def matches():
    return render_matches()


@matches_bp.route("/match/<int:match_id>")
def match_detail(match_id):
    return render_match_detail(match_id)


@matches_bp.route("/match/<int:match_id>/player/<int:player_id>")
def player_match_performance(match_id, player_id):
    return render_player_match_performance(match_id, player_id)
