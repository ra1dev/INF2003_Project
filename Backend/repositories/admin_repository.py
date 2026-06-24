"""Database operations for the small PostgreSQL/MongoDB CRUD demonstration."""

from datetime import datetime, timezone

from bson import ObjectId
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db
from Backend.mongo_conn import get_mongo_db


# PostgreSQL Match Notes -----------------------------------------------------

MATCH_NOTE_SELECT = """
    SELECT
        mn.note_id,
        mn.match_id,
        mn.note_title,
        mn.note_content,
        mn.created_at,
        mn.updated_at,
        mr.match_date,
        home.team_name AS home_team,
        away.team_name AS away_team
    FROM match_note mn
    INNER JOIN match_record mr ON mr.match_id = mn.match_id
    INNER JOIN team home ON home.team_id = mr.home_team_id
    INNER JOIN team away ON away.team_id = mr.away_team_id
"""


def list_match_notes(match_id=None, season_name=None, team_id=None):
    """READ notes, optionally restricted by match, season, or participating team."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = MATCH_NOTE_SELECT
        conditions = []
        params = []
        if match_id is not None:
            conditions.append("mn.match_id = %s")
            params.append(match_id)
        if season_name:
            conditions.append("mr.season_id = (SELECT season_id FROM season WHERE season_name = %s)")
            params.append(season_name)
        if team_id is not None:
            conditions.append("(mr.home_team_id = %s OR mr.away_team_id = %s)")
            params.extend([team_id, team_id])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY mn.updated_at DESC, mn.note_id DESC"
        cur.execute(query, params)
        return cur.fetchall()


def get_match_note(note_id):
    """READ one note for the edit form."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(MATCH_NOTE_SELECT + " WHERE mn.note_id = %s", (note_id,))
        return cur.fetchone()


def list_match_options():
    """Return fixtures for the match selector used by the create form."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                mr.match_id,
                mr.match_date,
                home.team_name AS home_team,
                away.team_name AS away_team
            FROM match_record mr
            INNER JOIN team home ON home.team_id = mr.home_team_id
            INNER JOIN team away ON away.team_id = mr.away_team_id
            ORDER BY mr.match_date DESC, mr.match_id DESC
            """
        )
        return cur.fetchall()


def list_note_filter_options():
    """Return seasons and teams used by the fixture-first Match Notes page."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT season_name
            FROM season
            ORDER BY start_year DESC
            """
        )
        seasons = cur.fetchall()
        cur.execute(
            """
            SELECT team_id, team_name
            FROM team
            ORDER BY team_name
            """
        )
        teams = cur.fetchall()
    return seasons, teams


def list_teams_for_season(season_name):
    """Return only teams that participated in the selected relational season."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT t.team_id, t.team_name
            FROM team t
            INNER JOIN (
                SELECT mr.home_team_id AS team_id
                FROM match_record mr
                INNER JOIN season s ON s.season_id = mr.season_id
                WHERE s.season_name = %s
                UNION
                SELECT mr.away_team_id AS team_id
                FROM match_record mr
                INNER JOIN season s ON s.season_id = mr.season_id
                WHERE s.season_name = %s
            ) participating ON participating.team_id = t.team_id
            ORDER BY t.team_name
            """,
            (season_name, season_name),
        )
        return cur.fetchall()


def list_filtered_matches(season_name, team_id=None):
    """READ fixtures for a selected season/team, including each note count."""
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = """
            SELECT
                mr.match_id,
                mr.match_date,
                s.season_name,
                home.team_name AS home_team,
                away.team_name AS away_team,
                mr.full_time_home_goals,
                mr.full_time_away_goals,
                COUNT(mn.note_id)::integer AS note_count
            FROM match_record mr
            INNER JOIN season s ON s.season_id = mr.season_id
            INNER JOIN team home ON home.team_id = mr.home_team_id
            INNER JOIN team away ON away.team_id = mr.away_team_id
            LEFT JOIN match_note mn ON mn.match_id = mr.match_id
            WHERE s.season_name = %s
        """
        params = [season_name]
        if team_id is not None:
            query += " AND (mr.home_team_id = %s OR mr.away_team_id = %s)"
            params.extend([team_id, team_id])
        query += """
            GROUP BY
                mr.match_id,
                mr.match_date,
                s.season_name,
                home.team_name,
                away.team_name,
                mr.full_time_home_goals,
                mr.full_time_away_goals
            ORDER BY mr.match_date DESC, mr.match_id DESC
        """
        cur.execute(query, params)
        return cur.fetchall()


def match_exists(match_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM match_record WHERE match_id = %s", (match_id,))
        return cur.fetchone() is not None


def create_match_note(match_id, note_title, note_content):
    """CREATE a PostgreSQL match note with a parameterized statement."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO match_note (match_id, note_title, note_content)
            VALUES (%s, %s, %s)
            RETURNING note_id
            """,
            (match_id, note_title, note_content),
        )
        note_id = cur.fetchone()[0]
    conn.commit()
    return note_id


def update_match_note(note_id, note_title, note_content):
    """UPDATE a PostgreSQL match note with a parameterized statement."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE match_note
            SET note_title = %s,
                note_content = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE note_id = %s
            """,
            (note_title, note_content, note_id),
        )
        updated = cur.rowcount > 0
    conn.commit()
    return updated


def delete_match_note(note_id):
    """DELETE a PostgreSQL match note by its primary key."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM match_note WHERE note_id = %s", (note_id,))
        deleted = cur.rowcount > 0
    conn.commit()
    return deleted


# MongoDB Match Event Annotations ------------------------------------------

def annotation_collection():
    collection = get_mongo_db().match_event_annotations
    collection.create_index("match_id", name="idx_annotation_match_id")
    collection.create_index(
        [("match_id", 1), ("event_minute", 1)],
        name="idx_annotation_match_minute",
    )
    collection.create_index("event_id", name="idx_annotation_event_id")
    return collection


def get_source_match_event(match_id, event_id):
    """READ one verified nested StatsBomb event from its MongoDB match document."""
    mongo_db = get_mongo_db()
    match_candidates = [match_id, str(match_id)]
    for collection_name in ("match_events", "events", "matchevents"):
        document = mongo_db[collection_name].find_one(
            {
                "app_match_id": {"$in": match_candidates},
                "events.id": event_id,
            },
            {"events": {"$elemMatch": {"id": event_id}}},
        )
        if document and document.get("events"):
            return document["events"][0]
    return None


def list_event_annotations(match_id=None, match_ids=None):
    """READ MongoDB annotations, optionally filtered by one or many matches."""
    if match_id is not None:
        query = {"match_id": match_id}
    elif match_ids is not None:
        query = {"match_id": {"$in": list(match_ids)}}
    else:
        query = {}
    return list(annotation_collection().find(query).sort("updated_at", -1))


def event_annotation_counts(match_ids):
    """Return annotation counts keyed by relational match ID."""
    match_ids = list(match_ids)
    if not match_ids:
        return {}
    rows = annotation_collection().aggregate(
        [
            {"$match": {"match_id": {"$in": match_ids}}},
            {"$group": {"_id": "$match_id", "count": {"$sum": 1}}},
        ]
    )
    return {row["_id"]: row["count"] for row in rows}


def event_coverage_seasons():
    """Return seasons represented by imported nested MongoDB event documents."""
    seasons = set()
    for value in get_mongo_db().match_events.distinct("season"):
        parts = str(value).split("/")
        if len(parts) == 2 and len(parts[1]) == 4:
            seasons.add(f"{parts[0]}/{parts[1][-2:]}")
        else:
            seasons.add(str(value))
    return seasons


def event_covered_match_ids(match_ids):
    """Return relational match IDs that have a MongoDB match_events document."""
    match_ids = list(match_ids)
    if not match_ids:
        return set()
    values = get_mongo_db().match_events.distinct(
        "app_match_id",
        {"app_match_id": {"$in": match_ids}},
    )
    return {int(value) for value in values}


def get_event_annotation(annotation_id):
    """READ one MongoDB annotation by ObjectId."""
    object_id = ObjectId(annotation_id)
    return annotation_collection().find_one({"_id": object_id})


def create_event_annotation(match_id, event, annotation, tags):
    """CREATE an annotation linked to a verified nested StatsBomb event."""
    now = datetime.now(timezone.utc)
    event_type = event.get("type") or {}
    player = event.get("player") or {}
    team = event.get("team") or {}
    result = annotation_collection().insert_one(
        {
            "match_id": match_id,
            "event_id": event.get("id"),
            "event_index": event.get("index"),
            "event_minute": event.get("minute", 0),
            "event_second": event.get("second", 0),
            "event_timestamp": event.get("timestamp"),
            "event_period": event.get("period"),
            "event_type": event_type.get("name") or "Unknown Event",
            "player": player.get("name"),
            "team": team.get("name"),
            "annotation": annotation,
            "tags": tags,
            "created_at": now,
            "updated_at": now,
        }
    )
    return result.inserted_id


def update_event_annotation(annotation_id, annotation, tags):
    """UPDATE user-authored fields while preserving the source event snapshot."""
    object_id = ObjectId(annotation_id)
    result = annotation_collection().update_one(
        {"_id": object_id},
        {
            "$set": {
                "annotation": annotation,
                "tags": tags,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return result.matched_count > 0


def delete_event_annotation(annotation_id):
    """DELETE a MongoDB event annotation by ObjectId."""
    object_id = ObjectId(annotation_id)
    result = annotation_collection().delete_one({"_id": object_id})
    return result.deleted_count > 0
