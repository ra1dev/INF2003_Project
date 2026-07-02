# Repository helpers for match listings, detail pages, and event formatting.
from flask import render_template, request
from psycopg2 import Error as PostgresError
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


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
        "event_id": event.get("id"),
        "event_index": event.get("index"),
        "timestamp": timestamp or "--:--",
        "minute": minute,
        "second": second,
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

    match_notes = []
    match_notes_error = None
    try:
        from Backend.repositories.admin_repository import list_match_notes

        match_notes = list_match_notes(match_id=match_id)
    except PostgresError as exc:
        conn.rollback()
        match_notes_error = f"Match notes are unavailable: {exc}"

    events = []
    key_events = []
    try:
        from Backend.mongo_conn import get_mongo_db
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

    event_annotations = []
    event_annotations_error = None
    try:
        from Backend.repositories.admin_repository import list_event_annotations

        event_annotations = list_event_annotations(match_id=match_id)
    except Exception as exc:
        event_annotations_error = f"Event annotations are unavailable: {exc}"

    return render_template(
        "match_detail.html",
        title="Match Stats",
        stats=stats,
        match=match,
        match_notes=match_notes,
        match_notes_error=match_notes_error,
        event_annotations=event_annotations,
        event_annotations_error=event_annotations_error,
        events=events,
        key_events=key_events
    )


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
        from Backend.mongo_conn import get_mongo_db
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


