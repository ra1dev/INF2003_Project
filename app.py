from flask import Flask, render_template, request, url_for
from psycopg2.extras import RealDictCursor
from Backend.db_conn import get_db, init_app
from Backend.mongo_conn import get_mongo_db

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

init_app(app)


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
        "player_name": player.get("name") or "Unknown player",
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


@app.route("/players")
def players():
    search = request.args.get("search")
    team = request.args.get("team")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT DISTINCT
            p.player_id,
            p.player_name,
            t.team_id,
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(COALESCE(t.team_name, 'Unknown Team'), ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo
        FROM player p
        LEFT JOIN player_team_season pts
            ON p.player_id = pts.player_id
        LEFT JOIN team t
            ON pts.team_id = t.team_id
        WHERE 1=1
    """

    params = []

    if search:
        query += " AND p.player_name ILIKE %s"
        params.append(f"%{search}%")

    if team:
        query += " AND t.team_name = %s"
        params.append(team)

    query += " ORDER BY p.player_name;"

    cur.execute(query, params)
    players = cur.fetchall()

    cur.execute("""
        SELECT team_name
        FROM team
        ORDER BY team_name;
    """)
    teams = cur.fetchall()

    cur.close()

    return render_template(
        "players.html",
        title="Players",
        players=players,
        teams=teams,
        search=search,
        selected_team=team
    )


@app.route("/player/<int:player_id>")
def player_detail(player_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            p.player_id,
            p.player_name,
            p.player_image,
            p.player_photo_url,

            s.season_name,

            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(COALESCE(t.team_name, 'Unknown Team'), ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,

            pos.position_name,

            pss.appearances,
            pss.goals,
            pss.assists,
            pss.shots,
            pss.shots_on_target,
            pss.big_chances_created,
            pss.passes,
            pss.crosses,
            pss.through_balls,
            pss.tackles,
            pss.interceptions,
            pss.clearances,
            pss.blocked_shots,
            pss.recoveries,
            pss.duels_won,
            pss.aerial_battles_won,
            pss.yellow_cards,
            pss.red_cards

        FROM player p
        INNER JOIN player_season_stats pss
            ON p.player_id = pss.player_id
        INNER JOIN season s
            ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON p.player_id = pts.player_id
           AND pss.season_id = pts.season_id
        LEFT JOIN team t
            ON pts.team_id = t.team_id
        LEFT JOIN position pos
            ON pss.position_id = pos.position_id
        WHERE p.player_id = %s
        ORDER BY s.season_name;
    """, (player_id,))

    stats = cur.fetchall()
    cur.close()

    player = None

    if stats:
        image_url = (
            stats[0]["player_image"]
            or stats[0]["player_photo_url"]
            or url_for("static", filename="images/player-placeholder.png")
        )

        total_appearances = sum(row["appearances"] or 0 for row in stats)
        total_goals = sum(row["goals"] or 0 for row in stats)
        total_assists = sum(row["assists"] or 0 for row in stats)
        total_shots = sum(row["shots"] or 0 for row in stats)
        total_shots_on_target = sum(row["shots_on_target"] or 0 for row in stats)
        total_big_chances_created = sum(row["big_chances_created"] or 0 for row in stats)
        total_passes = sum(row["passes"] or 0 for row in stats)
        total_crosses = sum(row["crosses"] or 0 for row in stats)
        total_through_balls = sum(row["through_balls"] or 0 for row in stats)
        total_tackles = sum(row["tackles"] or 0 for row in stats)
        total_interceptions = sum(row["interceptions"] or 0 for row in stats)
        total_clearances = sum(row["clearances"] or 0 for row in stats)
        total_blocked_shots = sum(row["blocked_shots"] or 0 for row in stats)
        total_recoveries = sum(row["recoveries"] or 0 for row in stats)
        total_duels_won = sum(row["duels_won"] or 0 for row in stats)
        total_aerial_battles_won = sum(row["aerial_battles_won"] or 0 for row in stats)
        total_yellow_cards = sum(row["yellow_cards"] or 0 for row in stats)
        total_red_cards = sum(row["red_cards"] or 0 for row in stats)

        player = {
            "player_id": stats[0]["player_id"],
            "player_name": stats[0]["player_name"],
            "team_name": stats[-1]["team_name"] or "Unknown Team",
            "team_logo": stats[-1]["team_logo"],
            "position_name": stats[-1]["position_name"],
            "image_url": image_url,

            "total_appearances": total_appearances,
            "total_goals": total_goals,
            "total_assists": total_assists,
            "total_shots": total_shots,
            "total_shots_on_target": total_shots_on_target,
            "total_big_chances_created": total_big_chances_created,
            "total_passes": total_passes,
            "total_crosses": total_crosses,
            "total_through_balls": total_through_balls,
            "total_tackles": total_tackles,
            "total_interceptions": total_interceptions,
            "total_clearances": total_clearances,
            "total_blocked_shots": total_blocked_shots,
            "total_recoveries": total_recoveries,
            "total_duels_won": total_duels_won,
            "total_aerial_battles_won": total_aerial_battles_won,
            "total_yellow_cards": total_yellow_cards,
            "total_red_cards": total_red_cards
        }

    return render_template(
        "player_detail.html",
        title="Player Stats",
        player=player,
        stats=stats
    )


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


@app.route("/predictions")
def predictions():
    return render_template(
        "predictions.html",
        title="Predictions",
        predictions=[],
        seasons=[],
        selected_season=None,
        search_team=None,
        search_opponent=None
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