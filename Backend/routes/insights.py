from flask import Blueprint, render_template, request, jsonify
from Backend.db_conn import get_db
from Backend.repositories.insights_repository import (
    get_clinical_finishing,
    get_shot_accuracy,
    get_home_dominance,
    get_away_resilience,
    get_discipline_risk,
    get_pressure_without_payoff,
    get_defensive_resistance,
)
from psycopg2.extras import RealDictCursor

insights_bp = Blueprint("insights", __name__)


def get_seasons(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT season_id, season_name
            FROM season
            ORDER BY start_year DESC
        """)
        return cur.fetchall()


@insights_bp.route("/insights")
def insights_page():
    conn = get_db()
    seasons = get_seasons(conn)

    season_id = request.args.get("season_id", type=int)

    if season_id is None and seasons:
        season_id = seasons[0]["season_id"]

    if season_id is None:
        return "No seasons found", 400

    clinical_finishing = get_clinical_finishing(conn, season_id)
    shot_accuracy = get_shot_accuracy(conn, season_id)
    home_dominance = get_home_dominance(conn, season_id)
    away_resilience = get_away_resilience(conn, season_id)
    discipline_risk = get_discipline_risk(conn, season_id)
    pressure_without_payoff = get_pressure_without_payoff(conn, season_id)
    defensive_resistance = get_defensive_resistance(conn, season_id)

    return render_template(
        "insights.html",
        title="Insights",
        season_id=season_id,
        seasons=seasons,
        clinical_finishing=clinical_finishing,
        shot_accuracy=shot_accuracy,
        home_dominance=home_dominance,
        away_resilience=away_resilience,
        discipline_risk=discipline_risk,
        pressure_without_payoff=pressure_without_payoff,
        defensive_resistance=defensive_resistance,
    )