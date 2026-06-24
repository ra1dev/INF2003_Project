import re
from datetime import datetime

from flask import render_template, request


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


NOSQL_INDEXES_READY = False

def ensure_nosql_indexes(mongo_db):
    """Create idempotent indexes used by the NoSQL dashboard and event search."""
    global NOSQL_INDEXES_READY
    if NOSQL_INDEXES_READY:
        return

    mongo_db.match_events.create_index("app_match_id", name="idx_match_events_app_match_id")
    mongo_db.match_events.create_index("season", name="idx_match_events_season")
    mongo_db.match_events.create_index("home_team", name="idx_match_events_home_team")
    mongo_db.match_events.create_index("away_team", name="idx_match_events_away_team")
    mongo_db.match_events.create_index("events.type.name", name="idx_match_events_event_type")
    mongo_db.match_events.create_index("events.player.name", name="idx_match_events_player_name")
    mongo_db.match_events.create_index("events.team.name", name="idx_match_events_team_name")
    mongo_db.match_events.create_index("events.minute", name="idx_match_events_minute")
    mongo_db.match_events.create_index("events.period", name="idx_match_events_period")
    mongo_db.player_match_performance.create_index("app_match_id", name="idx_player_perf_app_match_id")
    mongo_db.player_match_performance.create_index("player_name", name="idx_player_perf_player_name")
    mongo_db.player_match_performance.create_index("team_name", name="idx_player_perf_team_name")

    NOSQL_INDEXES_READY = True


def nosql_number(value, decimals=2):
    if value is None:
        return None
    return round(float(value), decimals)


def nosql_event_options(mongo_db):
    event_types = sorted(
        event_type
        for event_type in mongo_db.match_events.distinct("events.type.name")
        if event_type
    )
    teams = sorted({
        team
        for doc in mongo_db.match_events.find({}, {"home_team": 1, "away_team": 1})
        for team in (doc.get("home_team"), doc.get("away_team"))
        if team
    })
    matches = list(mongo_db.match_events.find(
        {},
        {"app_match_id": 1, "home_team": 1, "away_team": 1, "season": 1}
    ).sort("app_match_id", 1))
    players = sorted(
        player_name
        for player_name in mongo_db.match_events.distinct("events.player.name")
        if player_name
    )

    return event_types, teams, matches, players


def build_event_match_conditions(filters, field_prefix="events"):
    event_conditions = []

    if filters["team"]:
        event_conditions.append({f"{field_prefix}.team.name": filters["team"]})

    if filters["player"]:
        event_conditions.append({
            f"{field_prefix}.player.name": {
                "$regex": re.escape(filters["player"]),
                "$options": "i",
            }
        })

    if filters["event_type"]:
        event_conditions.append({f"{field_prefix}.type.name": filters["event_type"]})

    if filters["period"]:
        event_conditions.append({f"{field_prefix}.period": int(filters["period"])})

    minute_condition = {}
    if filters["minute_from"] is not None:
        minute_condition["$gte"] = filters["minute_from"]
    if filters["minute_to"] is not None:
        minute_condition["$lte"] = filters["minute_to"]
    if minute_condition:
        event_conditions.append({f"{field_prefix}.minute": minute_condition})

    if filters["key_moments_only"]:
        event_conditions.append({
            "$or": [
                {f"{field_prefix}.type.name": {"$in": ["Shot", "Substitution", "Own Goal For", "Own Goal Against"]}},
                {f"{field_prefix}.shot.outcome.name": {"$in": ["Goal", "Saved", "Blocked", "Off T", "Post"]}},
                {f"{field_prefix}.foul_committed.card.name": {"$exists": True}},
            ]
        })

    return event_conditions


def nosql_insights():
    error_message = None
    coverage = {}
    event_type_distribution = []
    top_players = []
    top_passers = []
    top_shooters = []
    team_activity = []
    defensive_activity = []
    discipline_summary = []
    cached_at = None

    try:
        from Backend.mongo_conn import get_mongo_db
        mongo_db = get_mongo_db()
        ensure_nosql_indexes(mongo_db)

        cache_collection = mongo_db["nosql_dashboard_cache"]
        if request.args.get("refresh") != "1":
            cache_doc = cache_collection.find_one({"_id": "nosql_insights_v1"})
            if cache_doc and cache_doc.get("payload"):
                payload = cache_doc["payload"]
                return render_template(
                    "nosql_insights.html",
                    title="Event Analytics Dashboard",
                    error_message=error_message,
                    coverage=payload.get("coverage", {}),
                    event_type_distribution=payload.get("event_type_distribution", []),
                    top_players=payload.get("top_players", []),
                    top_passers=payload.get("top_passers", []),
                    top_shooters=payload.get("top_shooters", []),
                    team_activity=payload.get("team_activity", []),
                    defensive_activity=payload.get("defensive_activity", []),
                    discipline_summary=payload.get("discipline_summary", []),
                    cached_at=payload.get("cached_at"),
                )

        event_count_row = next(mongo_db.match_events.aggregate([
            {"$project": {"event_count": {"$size": {"$ifNull": ["$events", []]}}}},
            {"$group": {"_id": None, "total_events": {"$sum": "$event_count"}}},
        ]), {"total_events": 0})

        coverage = {
            "matches": mongo_db.match_events.count_documents({}),
            "player_documents": mongo_db.player_match_performance.count_documents({}),
            "events": event_count_row["total_events"],
            "seasons": ", ".join(sorted(mongo_db.match_events.distinct("season"))) or "N/A",
        }

        event_facets = next(mongo_db.match_events.aggregate([
            {"$unwind": "$events"},
            {"$facet": {
                "event_type_distribution": [
                    {"$group": {"_id": "$events.type.name", "event_count": {"$sum": 1}}},
                    {"$match": {"_id": {"$ne": None}}},
                    {"$sort": {"event_count": -1}},
                    {"$limit": 12},
                    {"$project": {"_id": 0, "event_type": "$_id", "event_count": 1}},
                ],
                "defensive_activity": [
                    {"$match": {
                        "events.type.name": {
                            "$in": ["Pressure", "Duel", "Interception", "Clearance", "Block"]
                        }
                    }},
                    {"$group": {
                        "_id": {
                            "team_name": "$events.team.name",
                            "event_type": "$events.type.name",
                        },
                        "event_count": {"$sum": 1},
                    }},
                    {"$group": {
                        "_id": "$_id.team_name",
                        "total_defensive_events": {"$sum": "$event_count"},
                        "breakdown": {
                            "$push": {
                                "event_type": "$_id.event_type",
                                "event_count": "$event_count",
                            }
                        },
                    }},
                    {"$match": {"_id": {"$ne": None}}},
                    {"$sort": {"total_defensive_events": -1}},
                    {"$limit": 10},
                    {"$project": {
                        "_id": 0,
                        "team_name": "$_id",
                        "total_defensive_events": 1,
                        "breakdown": 1,
                    }},
                ],
                "discipline_summary": [
                    {"$match": {"events.type.name": "Foul Committed"}},
                    {"$group": {
                        "_id": "$events.team.name",
                        "fouls": {"$sum": 1},
                        "cards": {
                            "$sum": {
                                "$cond": [
                                    {"$ifNull": ["$events.foul_committed.card.name", False]},
                                    1,
                                    0,
                                ]
                            }
                        },
                        "yellow_cards": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": ["$events.foul_committed.card.name", "Yellow Card"]},
                                    1,
                                    0,
                                ]
                            }
                        },
                        "red_cards": {
                            "$sum": {
                                "$cond": [
                                    {"$in": ["$events.foul_committed.card.name", ["Red Card", "Second Yellow"]]},
                                    1,
                                    0,
                                ]
                            }
                        },
                    }},
                    {"$match": {"_id": {"$ne": None}}},
                    {"$sort": {"cards": -1, "fouls": -1}},
                    {"$limit": 10},
                    {"$project": {
                        "_id": 0,
                        "team_name": "$_id",
                        "fouls": 1,
                        "cards": 1,
                        "yellow_cards": 1,
                        "red_cards": 1,
                    }},
                ],
            }},
        ]), {})

        event_type_distribution = event_facets.get("event_type_distribution", [])
        defensive_activity = event_facets.get("defensive_activity", [])
        discipline_summary = event_facets.get("discipline_summary", [])

        top_players = list(mongo_db.player_match_performance.aggregate([
            {"$group": {
                "_id": "$player_name",
                "team_name": {"$first": "$team_name"},
                "matches": {"$sum": 1},
                "touches": {"$sum": "$statistics.touches"},
                "passes": {"$sum": "$statistics.passes"},
                "shots": {"$sum": "$statistics.shots"},
                "xg": {"$sum": "$statistics.xg"},
            }},
            {"$sort": {"touches": -1, "passes": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "player_name": "$_id",
                "team_name": 1,
                "matches": 1,
                "touches": 1,
                "passes": 1,
                "shots": 1,
                "xg": {"$round": ["$xg", 2]},
            }},
        ]))

        top_passers = list(mongo_db.player_match_performance.aggregate([
            {"$group": {
                "_id": "$player_name",
                "team_name": {"$first": "$team_name"},
                "matches": {"$sum": 1},
                "passes": {"$sum": "$statistics.passes"},
                "passes_completed": {"$sum": "$statistics.passes_completed"},
            }},
            {"$match": {"passes": {"$gte": 100}}},
            {"$addFields": {
                "pass_accuracy_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$passes_completed", "$passes"]}, 100]},
                        2,
                    ]
                }
            }},
            {"$sort": {"passes": -1, "pass_accuracy_pct": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "player_name": "$_id",
                "team_name": 1,
                "matches": 1,
                "passes": 1,
                "passes_completed": 1,
                "pass_accuracy_pct": 1,
            }},
        ]))

        top_shooters = list(mongo_db.player_match_performance.aggregate([
            {"$group": {
                "_id": "$player_name",
                "team_name": {"$first": "$team_name"},
                "matches": {"$sum": 1},
                "shots": {"$sum": "$statistics.shots"},
                "shots_on_target": {"$sum": "$statistics.shots_on_target"},
                "xg": {"$sum": "$statistics.xg"},
            }},
            {"$match": {"shots": {"$gt": 0}}},
            {"$addFields": {
                "shot_accuracy_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$shots_on_target", "$shots"]}, 100]},
                        2,
                    ]
                }
            }},
            {"$sort": {"xg": -1, "shots": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "player_name": "$_id",
                "team_name": 1,
                "matches": 1,
                "shots": 1,
                "shots_on_target": 1,
                "shot_accuracy_pct": 1,
                "xg": {"$round": ["$xg", 2]},
            }},
        ]))

        team_activity = list(mongo_db.player_match_performance.aggregate([
            {"$group": {
                "_id": "$team_name",
                "player_match_docs": {"$sum": 1},
                "touches": {"$sum": "$statistics.touches"},
                "passes": {"$sum": "$statistics.passes"},
                "shots": {"$sum": "$statistics.shots"},
                "fouls": {"$sum": "$statistics.fouls"},
                "tackles": {"$sum": "$statistics.tackles"},
                "interceptions": {"$sum": "$statistics.interceptions"},
                "xg": {"$sum": "$statistics.xg"},
            }},
            {"$sort": {"touches": -1}},
            {"$limit": 12},
            {"$project": {
                "_id": 0,
                "team_name": "$_id",
                "player_match_docs": 1,
                "touches": 1,
                "passes": 1,
                "shots": 1,
                "fouls": 1,
                "tackles": 1,
                "interceptions": 1,
                "xg": {"$round": ["$xg", 2]},
            }},
        ]))

        cached_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cache_collection.update_one(
            {"_id": "nosql_insights_v1"},
            {"$set": {
                "payload": {
                    "coverage": coverage,
                    "event_type_distribution": event_type_distribution,
                    "top_players": top_players,
                    "top_passers": top_passers,
                    "top_shooters": top_shooters,
                    "team_activity": team_activity,
                    "defensive_activity": defensive_activity,
                    "discipline_summary": discipline_summary,
                    "cached_at": cached_at,
                },
                "updated_at": cached_at,
            }},
            upsert=True,
        )

    except Exception as exc:
        error_message = f"MongoDB data is unavailable: {exc}"

    return render_template(
        "nosql_insights.html",
        title="Event Analytics Dashboard",
        error_message=error_message,
        coverage=coverage,
        event_type_distribution=event_type_distribution,
        top_players=top_players,
        top_passers=top_passers,
        top_shooters=top_shooters,
        team_activity=team_activity,
        defensive_activity=defensive_activity,
        discipline_summary=discipline_summary,
        cached_at=cached_at,
    )


def event_search():
    def parse_int(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    minute_from = parse_int(request.args.get("minute_from"))
    minute_to = parse_int(request.args.get("minute_to"))
    if minute_from is not None:
        minute_from = max(0, min(minute_from, 101))
    if minute_to is not None:
        minute_to = max(0, min(minute_to, 101))
    if minute_from is not None and minute_to is not None and minute_from > minute_to:
        minute_from, minute_to = minute_to, minute_from

    filters = {
        "team": request.args.get("team") or "",
        "player": request.args.get("player") or "",
        "event_type": request.args.get("event_type") or "",
        "match_id": parse_int(request.args.get("match_id")),
        "period": parse_int(request.args.get("period")),
        "minute_from": minute_from,
        "minute_to": minute_to,
        "key_moments_only": request.args.get("key_moments_only") == "1",
    }

    error_message = None
    event_types = []
    teams = []
    matches = []
    players = []
    events = []
    result_limit = 100
    has_more_results = False

    try:
        from Backend.mongo_conn import get_mongo_db
        mongo_db = get_mongo_db()
        ensure_nosql_indexes(mongo_db)
        event_types, teams, matches, players = nosql_event_options(mongo_db)

        pipeline = []
        if filters["match_id"] is not None:
            pipeline.append({"$match": {"app_match_id": filters["match_id"]}})

        pre_unwind_conditions = build_event_match_conditions(filters)
        if pre_unwind_conditions:
            pipeline.append({"$match": {"$and": pre_unwind_conditions}})

        pipeline.extend([
            {"$sort": {"app_match_id": 1}},
            {"$unwind": "$events"},
        ])

        event_conditions = build_event_match_conditions(filters)
        if event_conditions:
            pipeline.append({"$match": {"$and": event_conditions}})

        pipeline.extend([
            {"$limit": result_limit + 1},
            {"$project": {
                "_id": 0,
                "app_match_id": 1,
                "season": 1,
                "home_team": 1,
                "away_team": 1,
                "event": "$events",
            }},
        ])

        for row in mongo_db.match_events.aggregate(pipeline):
            if len(events) >= result_limit:
                has_more_results = True
                break
            formatted_event = format_statsbomb_event(row["event"])
            formatted_event.update({
                "match_id": row.get("app_match_id"),
                "season": row.get("season"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
            })
            events.append(formatted_event)
    except Exception as exc:
        error_message = f"MongoDB event search is unavailable: {exc}"

    return render_template(
        "event_search.html",
        title="Event Document Explorer",
        error_message=error_message,
        event_types=event_types,
        teams=teams,
        matches=matches,
        players=players,
        filters=filters,
        events=events,
        result_limit=result_limit,
        has_more_results=has_more_results,
    )


