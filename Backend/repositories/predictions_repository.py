from flask import render_template, request
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


def predictions():
    season = request.args.get("season")
    team = request.args.get("team")
    opponent = request.args.get("opponent")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            mr.match_date,
            s.season_name,
            home.team_name AS home_team,
            home.team_logo AS home_logo,
            away.team_name AS away_team,
            away.team_logo AS away_logo,
            p.home_win_probability,
            p.draw_probability,
            p.away_win_probability,
            p.predicted_result,
            p.actual_result
        FROM prediction p
        INNER JOIN match_record mr ON p.match_id = mr.match_id
        INNER JOIN season s ON mr.season_id = s.season_id
        INNER JOIN team home ON mr.home_team_id = home.team_id
        INNER JOIN team away ON mr.away_team_id = away.team_id
        WHERE 1=1
    """

    params = []

    if season:
        query += " AND s.season_name = %s"
        params.append(season)

    if team:
        query += " AND (home.team_name ILIKE %s OR away.team_name ILIKE %s)"
        params.extend([f"%{team}%", f"%{team}%"])

    if opponent:
        query += " AND (home.team_name ILIKE %s OR away.team_name ILIKE %s)"
        params.extend([f"%{opponent}%", f"%{opponent}%"])

    query += " ORDER BY mr.match_date DESC;"

    cur.execute(query, params)
    predictions = cur.fetchall()

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    cur.close()

    return render_template(
        "predictions.html",
        title="Predictions",
        predictions=predictions,
        seasons=seasons,
        selected_season=season,
        search_team=team,
        search_opponent=opponent
    )

