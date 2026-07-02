# Import StatsBomb match data into the local MongoDB database used by the NoSQL views.
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import ServerSelectionTimeoutError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR
PROJECT_ROOT = SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.mongo_player_performance import build_player_performance

load_dotenv(SCRIPT_DIR / ".env")

DEFAULT_MAPPING_CSV = REPO_ROOT / "data/statsbomb_to_app_match_map.csv"
DEFAULT_MATCHES_DIR = REPO_ROOT / "data/matches_epl"
DEFAULT_EVENTS_DIR = REPO_ROOT / "data/events_epl"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
MONGO_DB = os.getenv("MONGO_DB", "epl-db")


def load_match_map(mapping_csv: Path) -> dict[int, int]:
    with mapping_csv.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        required_columns = {"app_match_id", "statsbomb_match_id"}
        if not reader.fieldnames:
            raise ValueError(f"Mapping CSV is missing a header row: {mapping_csv}")

        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Mapping CSV is missing required columns {sorted(missing_columns)}: {mapping_csv}"
            )

        mapping: dict[int, int] = {}
        for row in reader:
            statsbomb_match_id = int(row["statsbomb_match_id"])
            app_match_id = int(row["app_match_id"])

            existing = mapping.get(statsbomb_match_id)
            if existing is not None and existing != app_match_id:
                raise ValueError(
                    f"Conflicting app_match_id values for statsbomb_match_id {statsbomb_match_id}"
                )

            mapping[statsbomb_match_id] = app_match_id

    return mapping


def load_match_metadata(matches_dir: Path) -> dict[int, dict[str, Any]]:
    metadata: dict[int, dict[str, Any]] = {}

    for matches_file in sorted(matches_dir.rglob("*.json")):
        if not matches_file.is_file():
            continue

        with matches_file.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        if isinstance(payload, dict):
            matches = [payload]
        elif isinstance(payload, list):
            matches = payload
        else:
            raise ValueError(
                f"Expected a list or object in {matches_file}, got {type(payload).__name__}"
            )

        for match in matches:
            if not isinstance(match, dict):
                continue

            statsbomb_match_id = match.get("match_id")
            if not isinstance(statsbomb_match_id, int):
                continue

            competition = match.get("competition") or {}
            if competition.get("competition_id") != 2:
                continue

            season = match.get("season") or {}
            home_team = match.get("home_team") or {}
            away_team = match.get("away_team") or {}

            metadata[statsbomb_match_id] = {
                "competition_id": competition.get("competition_id", 2),
                "season": season.get("season_name"),
                "home_team": home_team.get("home_team_name"),
                "away_team": away_team.get("away_team_name"),
            }

    return metadata


def load_events(event_file: Path) -> list[dict[str, Any]]:
    with event_file.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a list in {event_file}, got {type(payload).__name__}")

    events = [event for event in payload if isinstance(event, dict)]
    if len(events) != len(payload):
        raise ValueError(f"Found non-object event rows in {event_file}")

    return events


def open_match_events_collection(mongo_uri: str, mongo_db: str):
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.server_info()
    except ServerSelectionTimeoutError as error:
        client.close()
        raise RuntimeError(f"Could not connect to MongoDB: {error}") from error

    collection = client[mongo_db]["match_events"]
    collection.create_index(
        [("app_match_id", ASCENDING), ("statsbomb_match_id", ASCENDING)],
        unique=True,
        name="match_events_unique",
    )
    
    player_collection = client[mongo_db]["player_match_performance"]
    player_collection.create_index(
        [("app_match_id", ASCENDING), ("player_id", ASCENDING)],
        unique=True,
        name="player_match_performance_unique",
    )
    player_collection.create_index(
        [("player_name", ASCENDING), ("team_name", ASCENDING)],
        name="player_lookup",
    )
    
    return client, collection, player_collection


def reset_database(client: MongoClient, mongo_db: str) -> int:
    database = client[mongo_db]
    collection_names = database.list_collection_names()
    for collection_name in collection_names:
        database.drop_collection(collection_name)
    return len(collection_names)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import StatsBomb EPL match events into a local MongoDB database."
    )
    parser.add_argument("--mapping-csv", type=Path, default=DEFAULT_MAPPING_CSV)
    parser.add_argument("--matches-dir", type=Path, default=DEFAULT_MATCHES_DIR)
    parser.add_argument("--events-dir", type=Path, default=DEFAULT_EVENTS_DIR)
    parser.add_argument("--mongo-uri", default=MONGO_URI)
    parser.add_argument("--mongo-db", default=MONGO_DB)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset-db", action="store_true")
    parser.add_argument("--match-id", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.mapping_csv.exists():
        raise FileNotFoundError(f"Mapping CSV does not exist: {args.mapping_csv}")
    if not args.matches_dir.exists():
        raise FileNotFoundError(f"Matches directory does not exist: {args.matches_dir}")
    if not args.events_dir.exists():
        raise FileNotFoundError(f"Events directory does not exist: {args.events_dir}")

    match_map = load_match_map(args.mapping_csv)
    match_metadata = load_match_metadata(args.matches_dir)
    imported_at = datetime.now(timezone.utc)

    client = None
    collection = None
    player_collection = None
    if not args.dry_run:
        client, collection, player_collection = open_match_events_collection(args.mongo_uri, args.mongo_db)
        if args.reset_db:
            dropped_collections = reset_database(client, args.mongo_db)
            collection = client[args.mongo_db]["match_events"]
            collection.create_index(
                [("app_match_id", ASCENDING), ("statsbomb_match_id", ASCENDING)],
                unique=True,
                name="match_events_unique",
            )
            player_collection = client[args.mongo_db]["player_match_performance"]
            player_collection.create_index(
                [("app_match_id", ASCENDING), ("player_id", ASCENDING)],
                unique=True,
                name="player_match_performance_unique",
            )
            print(f"Reset database {args.mongo_db}; dropped {dropped_collections} collections.")

    processed_files = 0
    mapped_files = 0
    upserted_documents = 0
    skipped_unmapped = 0
    skipped_missing_metadata = 0

    try:
        for event_file in sorted(args.events_dir.rglob("*.json")):
            if not event_file.is_file():
                continue

            try:
                statsbomb_match_id = int(event_file.stem)
            except ValueError:
                continue

            if args.match_id is not None and statsbomb_match_id != args.match_id:
                continue

            processed_files += 1

            app_match_id = match_map.get(statsbomb_match_id)
            if app_match_id is None:
                skipped_unmapped += 1
                continue

            metadata = match_metadata.get(statsbomb_match_id)
            if metadata is None:
                skipped_missing_metadata += 1
                continue

            events = load_events(event_file)
            document = {
                "app_match_id": app_match_id,
                "statsbomb_match_id": statsbomb_match_id,
                "competition_id": metadata["competition_id"],
                "season": metadata["season"],
                "home_team": metadata["home_team"],
                "away_team": metadata["away_team"],
                "events": events,
                "imported_at": imported_at,
            }
            
            player_perf_docs = build_player_performance(events, metadata)

            mapped_files += 1
            if args.dry_run:
                print(
                    f"[dry-run] would upsert app_match_id={app_match_id} "
                    f"statsbomb_match_id={statsbomb_match_id} events={len(events)} "
                    f"players={len(player_perf_docs)}"
                )
                continue

            collection.update_one(
                {"app_match_id": app_match_id, "statsbomb_match_id": statsbomb_match_id},
                {"$set": document},
                upsert=True,
            )
            
            for player_doc in player_perf_docs:
                player_doc["app_match_id"] = app_match_id
                player_doc["statsbomb_match_id"] = statsbomb_match_id
                player_doc["match_date"] = None
                
                player_collection.update_one(
                    {"app_match_id": app_match_id, "player_id": player_doc["player_id"]},
                    {"$set": player_doc},
                    upsert=True,
                )
            
            upserted_documents += 1
    finally:
        if client is not None:
            client.close()

    print(f"Processed event files: {processed_files}")
    print(f"Mapped files: {mapped_files}")
    print(f"Upserted documents: {upserted_documents}")
    print(f"Skipped unmapped files: {skipped_unmapped}")
    print(f"Skipped files missing metadata: {skipped_missing_metadata}")
    if args.dry_run:
        print("Dry run completed; no MongoDB writes were made.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())