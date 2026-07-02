# Route handlers for the insights dashboard pages.
from flask import Blueprint, render_template, request
from Backend.db_conn import get_db
from Backend.repositories.insights_repository import (
    get_seasons,
    get_clinical_finishing,
    get_shot_accuracy,
    get_home_dominance,
    get_away_resilience,
    get_discipline_risk,
    get_pressure_without_payoff,
    get_defensive_resistance,
    get_player_shot_efficiency,
    get_player_team_contribution,
    get_player_creative_leverage,
    get_player_defensive_influence,
)

insights_bp = Blueprint("insights", __name__)


@insights_bp.route("/insights")
def insights_page():
    conn = get_db()
    seasons = get_seasons(conn)

    season_id = request.args.get("season_id", type=int)
    insight_view = request.args.get("view", "team")

    if insight_view not in {"team", "player"}:
        insight_view = "team"

    if season_id is None and seasons:
        season_id = seasons[0]["season_id"]

    if season_id is None:
        return "No seasons found", 400

    team_insights = {}
    player_insights = {}

    if insight_view == "player":
        player_insights = {
            "shot_efficiency": get_player_shot_efficiency(conn, season_id),
            "team_contribution": get_player_team_contribution(conn, season_id),
            "creative_leverage": get_player_creative_leverage(conn, season_id),
            "defensive_influence": get_player_defensive_influence(conn, season_id),
        }
    else:
        team_insights = {
            "clinical_finishing": get_clinical_finishing(conn, season_id),
            "shot_accuracy": get_shot_accuracy(conn, season_id),
            "home_dominance": get_home_dominance(conn, season_id),
            "away_resilience": get_away_resilience(conn, season_id),
            "discipline_risk": get_discipline_risk(conn, season_id),
            "pressure_without_payoff": get_pressure_without_payoff(conn, season_id),
            "defensive_resistance": get_defensive_resistance(conn, season_id),
        }

    return render_template(
        "insights.html",
        title="Insights",
        season_id=season_id,
        seasons=seasons,
        insight_view=insight_view,
        **team_insights,
        **player_insights,
    )
