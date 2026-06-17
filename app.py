from flask import Flask, render_template, request
from psycopg2.extras import RealDictCursor
from Backend.db_conn import get_db, init_app
from Backend.mongo_conn import get_mongo_db
from Backend.routes.insights import insights_bp
from Backend.routes.players import players_bp

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

init_app(app)

app.register_blueprint(insights_bp)
app.register_blueprint(players_bp)

def format_statsbomb_event(event):
    """Convert a raw StatsBomb event document into a UI-friendly row."""
    event_type = event.get("type") or {}
    player = event.get("player") or {}
    team = event.get("team") or {}
    possession_team = event.get("possession_team") or {}
    play_pattern = event.get("play_pattern") or {}
    period = event.get("period")
    minute = event.get("minute")
    second = event.get("second")
    timestamp = event.get("timestamp")
    if not timestamp and minute is not None:
        timestamp = f"{int(minute):02d}:{int(second or 0):02d}"

    description_parts = [event_type.get("name") or "Event"]

    if player.get("name"):
        description_parts.append(player["name"])
    if team.get("name"):
        description_parts.append(team["name"])

    location = event.get("location") or []
    if len(location) >= 2:
        location_label = f"({location[0]:.1f}, {location[1]:.1f})"
    else:
        location_label = ""

    end_location = event.get("pass", {}).get("end_location") if isinstance(event.get("pass"), dict) else None
    if not end_location and isinstance(event.get("carry"), dict):
        end_location = event.get("carry", {}).get("end_location")

    if isinstance(end_location, list) and len(end_location) >= 2:
        end_location_label = f"({end_location[0]:.1f}, {end_location[1]:.1f})"
    else:
        end_location_label = ""

    detail_bits = []
    context_bits = []

    if possession_team.get("name"):
        context_bits.append(f"Possession: {possession_team['name']}")
    if play_pattern.get("name"):
        context_bits.append(f"Pattern: {play_pattern['name']}")
    if event.get("duration") is not None:
        context_bits.append(f"Duration: {event['duration']:.1f}s")
    if event.get("under_pressure"):
        context_bits.append("Under pressure")

    pass_event = event.get("pass") if isinstance(event.get("pass"), dict) else {}
    shot_event = event.get("shot") if isinstance(event.get("shot"), dict) else {}
    foul_event = event.get("foul_committed") if isinstance(event.get("foul_committed"), dict) else {}
    substitution_event = event.get("substitution") if isinstance(event.get("substitution"), dict) else {}

    outcome = None
    if pass_event:
        recipient = (pass_event.get("recipient") or {}).get("name")
        pass_type = (pass_event.get("type") or {}).get("name")
        body_part = (pass_event.get("body_part") or {}).get("name")
        outcome = (pass_event.get("outcome") or {}).get("name")
        if recipient:
            detail_bits.append(f"to {recipient}")
        if pass_type:
            detail_bits.append(pass_type)
        if body_part:
            detail_bits.append(body_part)
        if outcome:
            detail_bits.append(outcome)
        if pass_event.get("length") is not None:
            detail_bits.append(f"{pass_event['length']:.1f}m")
        if end_location_label:
            detail_bits.append(f"End {end_location_label}")
    elif shot_event:
        outcome = (shot_event.get("outcome") or {}).get("name")
        technique = (shot_event.get("technique") or {}).get("name")
        body_part = (shot_event.get("body_part") or {}).get("name")
        if outcome:
            detail_bits.append(outcome)
        if technique:
            detail_bits.append(technique)
        if body_part:
            detail_bits.append(body_part)
        if shot_event.get("statsbomb_xg") is not None:
            detail_bits.append(f"xG {shot_event['statsbomb_xg']}")
        if end_location_label:
            detail_bits.append(f"End {end_location_label}")
    elif foul_event:
        card = (foul_event.get("card") or {}).get("name")
        if card:
            detail_bits.append(card)
    elif substitution_event:
        replacement = (substitution_event.get("replacement") or {}).get("name")
        if replacement:
            detail_bits.append(f"replaced by {replacement}")

    if not detail_bits:
        if event.get("location"):
            detail_bits.append(f"Location {location_label or 'unknown'}")

    if event.get("shot") and isinstance(event["shot"], dict):
        outcome = (event["shot"].get("outcome") or {}).get("name")
    elif event.get("pass") and isinstance(event["pass"], dict):
        outcome = (event["pass"].get("outcome") or {}).get("name")

    return {
        "timestamp": timestamp or "--:--",
        "period": period,
        "type_name": event_type.get("name") or "Event",
        "player_id": player.get("id"),
        "player_name": player.get("name") or "-",
        "team_name": team.get("name") or "Unknown team",
        "description": " - ".join(description_parts),
        "location_label": location_label,
        "end_location_label": end_location_label,
        "outcome": outcome,
        "details": " | ".join(context_bits + detail_bits),
        "is_key_moment": is_key_moment(event, event_type, shot_event, foul_event),
    }


def is_key_moment(event, event_type=None, shot_event=None, foul_event=None):
    event_type = event_type or (event.get("type") or {})
    shot_event = shot_event if shot_event is not None else (
        event.get("shot") if isinstance(event.get("shot"), dict) else {}
    )
    foul_event = foul_event if foul_event is not None else (
        event.get("foul_committed") if isinstance(event.get("foul_committed"), dict) else {}
    )

    event_type_name = event_type.get("name") or ""
    if event_type_name in {"Shot", "Substitution", "Own Goal For", "Own Goal Against"}:
        return True

    shot_outcome = (shot_event.get("outcome") or {}).get("name") if shot_event else None
    if shot_outcome in {"Goal", "Saved", "Blocked", "Off T", "Post"}:
        return True

    if foul_event and (foul_event.get("card") or {}).get("name"):
        return True

    return False


def find_match_events_document(mongo_db, match):
    collections = ["match_events", "events", "matchevents"]
    queries = [
        {"app_match_id": match["match_id"]},
        {"app_match_id": str(match["match_id"])},
    ]

    if match.get("home_team") and match.get("away_team") and match.get("season_name"):
        team_query = {
            "competition_id": 2,
            "season": match["season_name"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
        }
        queries.append(team_query)

    for collection_name in collections:
        collection = mongo_db[collection_name]
        for query in queries:
            document = collection.find_one(query)
            if document:
                return document

    return None


@app.route("/")
def home():
    return render_template("index.html", title="Home")


@app.route("/tables")
def tables():
    return render_template("tables.html", title="Database Tables")


@app.route("/teams")
def teams():
    search = request.args.get("search")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            team_id,
            team_name,
            COALESCE(
                team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo
        FROM team
        WHERE 1=1
    """

    params = []

    if search:
        query += " AND team_name ILIKE %s"
        params.append(f"%{search}%")

    query += " ORDER BY team_name;"

    cur.execute(query, params)
    teams = cur.fetchall()
    cur.close()

    return render_template(
        "teams.html",
        title="Teams",
        teams=teams,
        search=search
    )


@app.route("/team/<int:team_id>")
def team_detail(team_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,
            s.season_name,
            SUM(mts.goals) AS goals,
            SUM(mts.shots) AS shots,
            SUM(mts.shots_on_target) AS shots_on_target,
            SUM(mts.corners) AS corners,
            SUM(mts.fouls) AS fouls,
            SUM(mts.yellow_cards) AS yellow_cards,
            SUM(mts.red_cards) AS red_cards,
            ROUND(
                SUM(mts.goals)::decimal / NULLIF(SUM(mts.shots), 0) * 100,
                2
            ) AS goal_conversion
        FROM team t
        INNER JOIN match_team_stats mts
            ON t.team_id = mts.team_id
        INNER JOIN match_record mr
            ON mts.match_id = mr.match_id
        INNER JOIN season s
            ON mr.season_id = s.season_id
        WHERE t.team_id = %s
        GROUP BY t.team_name, t.team_logo, s.season_name
        ORDER BY s.season_name;
    """, (team_id,))

    stats = cur.fetchall()
    cur.close()

    return render_template(
        "team_detail.html",
        title="Team Stats",
        stats=stats
    )


@app.route("/matches")
def matches():
    season = request.args.get("season")
    team = request.args.get("team")
    opponent = request.args.get("opponent")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            mr.match_id,
            mr.match_date,
            s.season_name,

            home.team_name AS home_team,
            COALESCE(
                home.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(home.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS home_logo,

            away.team_name AS away_team,
            COALESCE(
                away.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(away.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS away_logo,

            mr.full_time_home_goals,
            mr.full_time_away_goals,
            mr.full_time_result
        FROM match_record mr
        INNER JOIN season s 
            ON mr.season_id = s.season_id
        INNER JOIN team home 
            ON mr.home_team_id = home.team_id
        INNER JOIN team away 
            ON mr.away_team_id = away.team_id
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

    query += " ORDER BY mr.match_date DESC LIMIT 100;"

    cur.execute(query, params)
    matches = cur.fetchall()

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    cur.close()

    return render_template(
        "matches.html",
        title="Matches",
        matches=matches,
        seasons=seasons,
        selected_season=season,
        search_team=team,
        search_opponent=opponent
    )


@app.route("/match/<int:match_id>")
def match_detail(match_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            mr.match_id,
            mr.match_date,
            s.season_name,
            home.team_name AS home_team,
            away.team_name AS away_team,
            mr.full_time_home_goals,
            mr.full_time_away_goals
        FROM match_record mr
        INNER JOIN team home 
            ON mr.home_team_id = home.team_id
        INNER JOIN team away 
            ON mr.away_team_id = away.team_id
        INNER JOIN season s
            ON mr.season_id = s.season_id
        WHERE mr.match_id = %s;
    """, (match_id,))

    match = cur.fetchone()

    cur.execute("""
        SELECT
            mts.is_home,
            t.team_id,
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,
            mts.goals,
            mts.shots,
            mts.shots_on_target,
            mts.corners,
            mts.fouls,
            mts.yellow_cards,
            mts.red_cards
        FROM match_team_stats mts
        INNER JOIN team t
            ON mts.team_id = t.team_id
        WHERE mts.match_id = %s
        ORDER BY mts.is_home DESC;
    """, (match_id,))

    stats = cur.fetchall()
    cur.close()

    events = []
    key_events = []
    try:
        mongo_db = get_mongo_db()
        match_doc = find_match_events_document(mongo_db, match)
        raw_events = (match_doc or {}).get("events", [])
        events = sorted(
            (format_statsbomb_event(event) for event in raw_events),
            key=lambda item: (
                item["timestamp"] == "--:--",
                item["timestamp"],
                item["period"] or 0,
            )
        )
        key_events = [event for event in events if event.get("is_key_moment")]
    except Exception:
        events = []
        key_events = []

    return render_template(
        "match_detail.html",
        title="Match Stats",
        stats=stats,
        match=match,
        events=events,
        key_events=key_events
    )


@app.route("/match/<int:match_id>/player/<int:player_id>")
def player_match_performance(match_id, player_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            mr.match_id,
            mr.match_date,
            s.season_name,
            home.team_name AS home_team,
            away.team_name AS away_team,
            mr.full_time_home_goals,
            mr.full_time_away_goals
        FROM match_record mr
        INNER JOIN season s ON mr.season_id = s.season_id
        INNER JOIN team home ON mr.home_team_id = home.team_id
        INNER JOIN team away ON mr.away_team_id = away.team_id
        WHERE mr.match_id = %s;
    """, (match_id,))

    match = cur.fetchone()
    cur.close()

    if not match:
        return render_template("404.html", message="Match not found"), 404

    player_perf = None
    try:
        mongo_db = get_mongo_db()
        player_collection = mongo_db["player_match_performance"]
        player_perf = player_collection.find_one({"player_id": player_id, "match_id": match_id})
        
        if not player_perf:
            player_collection = mongo_db["player_match_performance"]
            player_perf = player_collection.find_one({"player_id": player_id})
            
            if player_perf and player_perf.get("app_match_id"):
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    "SELECT match_id FROM match_record WHERE match_id = %s;",
                    (match_id,)
                )
                if not cur.fetchone():
                    player_perf = None
                cur.close()
    except Exception:
        player_perf = None

    if not player_perf:
        return render_template(
            "player_match_performance.html",
            title="Player Performance",
            match=match,
            player_perf=None,
            error="Player performance data not found for this match."
        ), 404

    return render_template(
        "player_match_performance.html",
        title="Player Performance",
        match=match,
        player_perf=player_perf
    )


@app.route("/predictions")
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

@app.route("/season-recap")
def season_recap():
    selected_season = request.args.get("season")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    if not selected_season and seasons:
        selected_season = seasons[-1]["season_name"]

    cur.execute("""
        SELECT
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,
            SUM(CASE
                WHEN mts.is_home AND mr.full_time_home_goals > mr.full_time_away_goals THEN 3
                WHEN NOT mts.is_home AND mr.full_time_away_goals > mr.full_time_home_goals THEN 3
                WHEN mr.full_time_home_goals = mr.full_time_away_goals THEN 1
                ELSE 0
            END) AS pts
        FROM match_team_stats mts
        JOIN match_record mr ON mts.match_id = mr.match_id
        JOIN team t ON mts.team_id = t.team_id
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s
        GROUP BY t.team_name, t.team_logo
        ORDER BY pts DESC
        LIMIT 1;
    """, (selected_season,))
    champion = cur.fetchone()

    cur.execute("""
        SELECT
            COUNT(DISTINCT mr.match_id) AS total_matches,
            SUM(mr.full_time_home_goals + mr.full_time_away_goals) AS total_goals,
            ROUND(
                SUM(mr.full_time_home_goals + mr.full_time_away_goals)::decimal /
                NULLIF(COUNT(DISTINCT mr.match_id), 0), 2
            ) AS avg_goals
        FROM match_record mr
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s;
    """, (selected_season,))
    goal_kpis = cur.fetchone()

    cur.execute("""
        SELECT
            SUM(mts.yellow_cards) AS total_yellow,
            SUM(mts.red_cards)    AS total_red
        FROM match_team_stats mts
        JOIN match_record mr ON mts.match_id = mr.match_id
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s;
    """, (selected_season,))
    card_kpis = cur.fetchone()

    cur.execute("""
        SELECT
            p.player_name,
            pss.goals,
            t.team_name
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.goals IS NOT NULL
        ORDER BY pss.goals DESC
        LIMIT 1;
    """, (selected_season,))
    top_scorer = cur.fetchone()

    cur.execute("""
        SELECT
            p.player_name,
            pss.clean_sheets,
            t.team_name
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.clean_sheets IS NOT NULL
        ORDER BY pss.clean_sheets DESC
        LIMIT 1;
    """, (selected_season,))
    top_cs = cur.fetchone()

    cur.execute("""
        SELECT
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,
            COUNT(DISTINCT mts.match_id) AS played,
            SUM(CASE
                WHEN mts.is_home AND mr.full_time_home_goals > mr.full_time_away_goals THEN 1
                WHEN NOT mts.is_home AND mr.full_time_away_goals > mr.full_time_home_goals THEN 1
                ELSE 0 END) AS wins,
            SUM(CASE WHEN mr.full_time_home_goals = mr.full_time_away_goals THEN 1 ELSE 0 END) AS draws,
            SUM(CASE
                WHEN mts.is_home AND mr.full_time_home_goals < mr.full_time_away_goals THEN 1
                WHEN NOT mts.is_home AND mr.full_time_away_goals < mr.full_time_home_goals THEN 1
                ELSE 0 END) AS losses,
            SUM(mts.goals) AS gf,
            SUM(CASE
                WHEN mts.is_home THEN mr.full_time_away_goals
                ELSE mr.full_time_home_goals
            END) AS ga,
            SUM(mts.goals) - SUM(CASE
                WHEN mts.is_home THEN mr.full_time_away_goals
                ELSE mr.full_time_home_goals
            END) AS gd,
            SUM(CASE
                WHEN mts.is_home AND mr.full_time_home_goals > mr.full_time_away_goals THEN 3
                WHEN NOT mts.is_home AND mr.full_time_away_goals > mr.full_time_home_goals THEN 3
                WHEN mr.full_time_home_goals = mr.full_time_away_goals THEN 1
                ELSE 0 END) AS pts
        FROM match_team_stats mts
        JOIN match_record mr ON mts.match_id = mr.match_id
        JOIN team t ON mts.team_id = t.team_id
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s
        GROUP BY t.team_name, t.team_logo
        ORDER BY pts DESC, gd DESC, gf DESC;
    """, (selected_season,))
    standings = cur.fetchall()

    cur.execute("""
        SELECT
            SUM(CASE WHEN mr.full_time_result = 'H' THEN 1 ELSE 0 END) AS home_wins,
            SUM(CASE WHEN mr.full_time_result = 'D' THEN 1 ELSE 0 END) AS draws,
            SUM(CASE WHEN mr.full_time_result = 'A' THEN 1 ELSE 0 END) AS away_wins
        FROM match_record mr
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s;
    """, (selected_season,))
    outcomes = cur.fetchone()

    cur.execute("""
        SELECT
            t.team_name,
            SUM(mts.goals) AS goals_scored
        FROM match_team_stats mts
        JOIN team t ON mts.team_id = t.team_id
        JOIN match_record mr ON mts.match_id = mr.match_id
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s
        GROUP BY t.team_name
        ORDER BY goals_scored DESC
        LIMIT 10;
    """, (selected_season,))
    goals_by_team = cur.fetchall()

    cur.execute("""
        SELECT
            t.team_name,
            SUM(mts.yellow_cards) AS yellow_cards,
            SUM(mts.red_cards)    AS red_cards
        FROM match_team_stats mts
        JOIN team t ON mts.team_id = t.team_id
        JOIN match_record mr ON mts.match_id = mr.match_id
        JOIN season s ON mr.season_id = s.season_id
        WHERE s.season_name = %s
        GROUP BY t.team_name
        ORDER BY yellow_cards DESC
        LIMIT 8;
    """, (selected_season,))
    discipline = cur.fetchall()

    cur.execute("""
        SELECT p.player_name, t.team_name, pss.goals AS val
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.goals IS NOT NULL
        ORDER BY pss.goals DESC LIMIT 8;
    """, (selected_season,))
    goals_leaders = cur.fetchall()

    cur.execute("""
        SELECT p.player_name, t.team_name, pss.assists AS val
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.assists IS NOT NULL
        ORDER BY pss.assists DESC LIMIT 8;
    """, (selected_season,))
    assists_leaders = cur.fetchall()

    cur.execute("""
        SELECT p.player_name, t.team_name, pss.clean_sheets AS val
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.clean_sheets IS NOT NULL
        ORDER BY pss.clean_sheets DESC LIMIT 8;
    """, (selected_season,))
    cs_leaders = cur.fetchall()

    cur.execute("""
        SELECT p.player_name, t.team_name, pss.tackles AS val
        FROM player_season_stats pss
        JOIN player p ON pss.player_id = p.player_id
        JOIN season s ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON pts.player_id = p.player_id AND pts.season_id = pss.season_id
        LEFT JOIN team t ON pts.team_id = t.team_id
        WHERE s.season_name = %s AND pss.tackles IS NOT NULL
        ORDER BY pss.tackles DESC LIMIT 8;
    """, (selected_season,))
    tackles_leaders = cur.fetchall()

    cur.close()

    return render_template(
        "season_recap.html",
        title="Season Recap",
        seasons=seasons,
        selected_season=selected_season,
        champion=champion,
        goal_kpis=goal_kpis,
        card_kpis=card_kpis,
        top_scorer=top_scorer,
        top_cs=top_cs,
        standings=standings,
        outcomes=outcomes,
        goals_by_team=goals_by_team,
        discipline=discipline,
        goals_leaders=goals_leaders,
        assists_leaders=assists_leaders,
        cs_leaders=cs_leaders,
        tackles_leaders=tackles_leaders
    )


@app.route("/season-table")
def season_table():
    selected_season = request.args.get("season")
    selected_week = request.args.get("week", type=int)

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    if not selected_season and seasons:
        selected_season = seasons[-1]["season_name"]

    cur.execute("""
        SELECT
            mr.match_id,
            mr.match_date,
            mr.home_team_id,
            mr.away_team_id,
            mr.full_time_home_goals,
            mr.full_time_away_goals,
            ht.team_name AS home_team_name,
            ht.team_logo AS home_team_logo,
            at.team_name AS away_team_name,
            at.team_logo AS away_team_logo
        FROM match_record mr
        JOIN season s ON mr.season_id = s.season_id
        JOIN team ht ON mr.home_team_id = ht.team_id
        JOIN team at ON mr.away_team_id = at.team_id
        WHERE s.season_name = %s
        ORDER BY mr.match_date ASC, mr.match_id ASC;
    """, (selected_season,))
    match_rows = cur.fetchall()

    cur.close()

    weekly_matches = []

    for idx, row in enumerate(match_rows):
        if idx % 10 == 0:
            week_number = idx // 10 + 1
            weekly_matches.append({
                "week": week_number,
                "match_date": row["match_date"].isoformat(),
                "matches": [],
            })
        weekly_matches[-1]["matches"].append(row)

    def start_team_record(team_id, team_name, team_logo):
        return {
            "team_id": team_id,
            "team_name": team_name,
            "team_logo": team_logo or (
                'https://ui-avatars.com/api/?name=' + team_name.replace(' ', '+') +
                '&background=1e293b&color=ffffff&size=128'
            ),
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "gf": 0,
            "ga": 0,
            "gd": 0,
            "pts": 0,
        }

    team_state = {}
    sorted_week_snapshots = []

    for week_index, week in enumerate(weekly_matches, start=1):
        for match in week["matches"]:
            home_id = match["home_team_id"]
            away_id = match["away_team_id"]
            if home_id not in team_state:
                team_state[home_id] = start_team_record(
                    home_id,
                    match["home_team_name"],
                    match["home_team_logo"],
                )
            if away_id not in team_state:
                team_state[away_id] = start_team_record(
                    away_id,
                    match["away_team_name"],
                    match["away_team_logo"],
                )

            home = team_state[home_id]
            away = team_state[away_id]
            home_goals = match["full_time_home_goals"]
            away_goals = match["full_time_away_goals"]

            home["played"] += 1
            away["played"] += 1
            home["gf"] += home_goals
            home["ga"] += away_goals
            away["gf"] += away_goals
            away["ga"] += home_goals

            if home_goals > away_goals:
                home["wins"] += 1
                away["losses"] += 1
                home["pts"] += 3
            elif home_goals < away_goals:
                away["wins"] += 1
                home["losses"] += 1
                away["pts"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["pts"] += 1
                away["pts"] += 1

            home["gd"] = home["gf"] - home["ga"]
            away["gd"] = away["gf"] - away["ga"]

        standings = sorted(
            [dict(team) for team in team_state.values()],
            key=lambda team: (
                -team["pts"],
                -team["gd"],
                -team["gf"],
                team["team_name"],
            )
        )
        for position, team in enumerate(standings, start=1):
            team["position"] = position

        sorted_week_snapshots.append({
            "week": week_index,
            "match_date": week["match_date"],
            "standings": standings,
        })

    for index, snapshot in enumerate(sorted_week_snapshots):
        previous = sorted_week_snapshots[index - 1]["standings"] if index > 0 else []
        previous_positions = {team["team_name"]: team["position"] for team in previous}
        for team in snapshot["standings"]:
            prior_position = previous_positions.get(team["team_name"])
            if prior_position is None:
                team["movement"] = None
                team["movement_delta"] = 0
            else:
                team["movement_delta"] = abs(team["position"] - prior_position)
                if team["position"] < prior_position:
                    team["movement"] = "up"
                elif team["position"] > prior_position:
                    team["movement"] = "down"
                else:
                    team["movement"] = None
                    team["movement_delta"] = 0

    if selected_week is None:
        selected_week = 1
    if selected_week < 1:
        selected_week = 1
    if selected_week > len(sorted_week_snapshots):
        selected_week = len(sorted_week_snapshots) if sorted_week_snapshots else 1

    return render_template(
        "season_table.html",
        title="Season Table",
        seasons=seasons,
        selected_season=selected_season,
        selected_week=selected_week,
        weeks=sorted_week_snapshots,
        week_tables=sorted_week_snapshots,
    )


@app.route("/db")
def db_test():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM player LIMIT 10;")
    players = cur.fetchall()

    cur.close()

    return str(players)


if __name__ == "__main__":
    app.run(debug=True)
