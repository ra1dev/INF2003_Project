from flask import Blueprint

from Backend.repositories.player_comparison_repository import player_comparison as render_player_comparison

player_comparison_bp = Blueprint("player_comparison", __name__)


@player_comparison_bp.route("/player-comparison")
def player_comparison():
    return render_player_comparison()
