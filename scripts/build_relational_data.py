# Build and clean the relational dataset used by the Flask application.
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "data" / "reports"

MATCH_FILE = ROOT / "epl_matches_2000_2025.csv"
PLAYER_FILES = [
    ROOT / "pl_15-16.csv",
    ROOT / "pl_16-17.csv",
    ROOT / "pl_17-18.csv",
    ROOT / "pl_18-19.csv",
    ROOT / "pl_19-20.csv",
    ROOT / "pl_20-21.csv",
    ROOT / "pl_21-22.csv",
    ROOT / "pl_22-23.csv",
    ROOT / "pl_23-24.csv",
]
PLAYER_CLUB_FILE = ROOT / "teammate_dump" / "pl_player.csv"
MANUAL_CORRECTIONS_FILE = ROOT / "data" / "manual_corrections.json"

TARGET_SEASONS = [
    "2015/16",
    "2016/17",
    "2017/18",
    "2018/19",
    "2019/20",
    "2020/21",
    "2021/22",
]

TEAM_ALIASES = {
    "AFC Bournemouth": "Bournemouth",
    "Brighton and Hove Albion": "Brighton",
    "Cardiff City": "Cardiff",
    "Huddersfield Town": "Huddersfield",
    "Hull City": "Hull",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Middlesbrough": "Middlesbrough",
    "Newcastle United": "Newcastle",
    "Norwich City": "Norwich",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield United",
    "Stoke City": "Stoke",
    "Swansea City": "Swansea",
    "Tottenham Hotspur": "Tottenham",
    "West Bromwich Albion": "West Brom",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
}

PLAYER_HEADER_MAP = {
    "Name": "player_name",
    "Position": "position_name",
    "Appearances": "appearances",
    "Clean sheets": "clean_sheets",
    "Goals conceded": "goals_conceded",
    "Goals Conceded": "goals_conceded",
    "Tackles": "tackles",
    "Tackle success %": "tackle_success_pct",
    "Last man tackles": "last_man_tackles",
    "Blocked shots": "blocked_shots",
    "Interceptions": "interceptions",
    "Clearances": "clearances",
    "Headed Clearance": "headed_clearances",
    "Clearances off line": "clearances_off_line",
    "Recoveries": "recoveries",
    "Duels won": "duels_won",
    "Duels lost": "duels_lost",
    "Successful 50/50s": "successful_50_50s",
    "Aerial battles won": "aerial_battles_won",
    "Aerial battles lost": "aerial_battles_lost",
    "Own goals": "own_goals",
    "Errors leading to goal": "errors_leading_to_goal",
    "Assists": "assists",
    "Passes": "passes",
    "Passes per match": "passes_per_match",
    "Big chances created": "big_chances_created",
    "Big Chances Created": "big_chances_created",
    "Crosses": "crosses",
    "Cross accuracy %": "cross_accuracy_pct",
    "Through balls": "through_balls",
    "Accurate long balls": "accurate_long_balls",
    "Yellow cards": "yellow_cards",
    "Red cards": "red_cards",
    "Fouls": "fouls",
    "Offsides": "offsides",
    "Goals": "goals",
    "Headed goals": "headed_goals",
    "Goals with right foot": "goals_with_right_foot",
    "Goals with left foot": "goals_with_left_foot",
    "Hit woodwork": "hit_woodwork",
    "Goals per match": "goals_per_match",
    "Penalties scored": "penalties_scored",
    "Freekicks scored": "freekicks_scored",
    "Shots": "shots",
    "Shots on target": "shots_on_target",
    "Shooting accuracy %": "shooting_accuracy_pct",
    "Big chances missed": "big_chances_missed",
    "Saves": "saves",
    "Penalties saved": "penalties_saved",
    "Penalties Saved": "penalties_saved",
    "Punches": "punches",
    "High Claims": "high_claims",
    "Catches": "catches",
    "Sweeper clearances": "sweeper_clearances",
    "Throw outs": "throw_outs",
    "Goal Kicks": "goal_kicks",
}

STAGING_PLAYER_COLUMNS = [
    "source_file",
    "season_name",
    "player_name",
    "position_name",
    "appearances",
    "clean_sheets",
    "goals_conceded",
    "tackles",
    "tackle_success_pct",
    "last_man_tackles",
    "blocked_shots",
    "interceptions",
    "clearances",
    "headed_clearances",
    "clearances_off_line",
    "recoveries",
    "duels_won",
    "duels_lost",
    "successful_50_50s",
    "aerial_battles_won",
    "aerial_battles_lost",
    "own_goals",
    "errors_leading_to_goal",
    "assists",
    "passes",
    "passes_per_match",
    "big_chances_created",
    "crosses",
    "cross_accuracy_pct",
    "through_balls",
    "accurate_long_balls",
    "yellow_cards",
    "red_cards",
    "fouls",
    "offsides",
    "goals",
    "headed_goals",
    "goals_with_right_foot",
    "goals_with_left_foot",
    "hit_woodwork",
    "goals_per_match",
    "penalties_scored",
    "freekicks_scored",
    "shots",
    "shots_on_target",
    "shooting_accuracy_pct",
    "big_chances_missed",
    "saves",
    "penalties_saved",
    "punches",
    "high_claims",
    "catches",
    "sweeper_clearances",
    "throw_outs",
    "goal_kicks",
]

PLAYER_FINAL_STAT_COLUMNS = [
    "appearances",
    "clean_sheets",
    "goals_conceded",
    "tackles",
    "tackle_success_pct",
    "last_man_tackles",
    "blocked_shots",
    "interceptions",
    "clearances",
    "headed_clearances",
    "clearances_off_line",
    "recoveries",
    "duels_won",
    "duels_lost",
    "successful_50_50s",
    "aerial_battles_won",
    "aerial_battles_lost",
    "own_goals",
    "errors_leading_to_goal",
    "assists",
    "passes",
    "big_chances_created",
    "crosses",
    "cross_accuracy_pct",
    "through_balls",
    "accurate_long_balls",
    "yellow_cards",
    "red_cards",
    "fouls",
    "offsides",
    "goals",
    "headed_goals",
    "goals_with_right_foot",
    "goals_with_left_foot",
    "hit_woodwork",
    "penalties_scored",
    "freekicks_scored",
    "shots",
    "shots_on_target",
    "shooting_accuracy_pct",
    "big_chances_missed",
    "saves",
    "penalties_saved",
    "punches",
    "high_claims",
    "catches",
    "sweeper_clearances",
    "throw_outs",
    "goal_kicks",
]

INTEGER_COLUMNS = {
    column for column in PLAYER_FINAL_STAT_COLUMNS if not column.endswith("_pct")
}

DEFAULT_CORRECTIONS = {
    "match_stat_corrections": [
        {
            "season": "2021/22",
            "match_date": "2021-08-15",
            "home_team": "Newcastle",
            "away_team": "West Ham",
            "field": "AwayShots",
            "raw_value": "8",
            "corrected_value": "18",
            "reason": "Original row has AwayShotsOnTarget=9, which cannot exceed AwayShots=8. ESPN and StatMuse report West Ham had 18 shots and 9 shots on target.",
            "sources": [
                "https://www.espn.com/soccer/match/_/gameId/606037/west-ham-united-newcastle-united",
                "https://www.statmuse.com/fc/match/8-15-2021-new-vs-whu-11656",
            ],
        }
    ],
    "rejected_player_stat_rows": [
        {
            "source_file": "pl_16-17.csv",
            "name": "Dean Marney",
            "season_name": "2016/17",
            "reason": "Source row reports 96 appearances in a 38-match league season.",
        },
        {
            "source_file": "pl_16-17.csv",
            "name": "Nacer Chadli",
            "season_name": "2016/17",
            "reason": "Source row reports 124 appearances in a 38-match league season.",
        },
        {
            "source_file": "pl_18-19.csv",
            "name": "Alex Pritchard",
            "season_name": "2018/19",
            "reason": "Source row reports 48 appearances in a 38-match league season.",
        },
        {
            "source_file": "pl_18-19.csv",
            "name": "Yannick Bolasie",
            "season_name": "2018/19",
            "reason": "Source row reports 119 appearances in a 38-match league season.",
        },
    ],
}


@dataclass(frozen=True)
class PlayerKey:
    normalized_name: str


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_player_name(value: str) -> str:
    value = normalize_space(value).casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_space(value)


def season_from_player_file(path: Path) -> str:
    match = re.search(r"pl_(\d{2})-(\d{2})\.csv$", path.name)
    if not match:
        raise ValueError(f"Cannot infer season from {path}")
    start = 2000 + int(match.group(1))
    return f"{start}/{match.group(2)}"


def full_source_season_to_short(value: str) -> str:
    start, end = value.split("/")
    return f"{start}/{end[-2:]}"


def season_years(season_name: str) -> tuple[int, int]:
    start = int(season_name[:4])
    return start, start + 1


def parse_int(value: str | None) -> int | None:
    value = normalize_space(value)
    if value == "":
        return None
    return int(value.replace(",", ""))


def parse_pct(value: str | None) -> str | None:
    value = normalize_space(value)
    if value == "":
        return None
    if value.endswith("%"):
        value = value[:-1]
    return f"{float(value):.2f}"


def parse_count(value: str | None) -> int | None:
    return parse_int(value)


def clean_team_name(value: str) -> str:
    value = normalize_space(value)
    return TEAM_ALIASES.get(value, value)


def read_csv(path: Path, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    with path.open(newline="", encoding=encoding) as fh:
        return list(csv.DictReader(fh))


def load_corrections() -> dict[str, object]:
    if not MANUAL_CORRECTIONS_FILE.exists():
        MANUAL_CORRECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        MANUAL_CORRECTIONS_FILE.write_text(
            json.dumps(DEFAULT_CORRECTIONS, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return json.loads(MANUAL_CORRECTIONS_FILE.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def clean_player_raw_row(source_file: Path, season_name: str, row: dict[str, str]) -> dict[str, str]:
    cleaned = {column: "" for column in STAGING_PLAYER_COLUMNS}
    cleaned["source_file"] = source_file.name
    cleaned["season_name"] = season_name
    for source_name, target_name in PLAYER_HEADER_MAP.items():
        if source_name in row:
            cleaned[target_name] = normalize_space(row[source_name])
    return cleaned


def typed_player_stat_row(row: dict[str, str]) -> dict[str, object]:
    typed: dict[str, object] = {}
    for column in PLAYER_FINAL_STAT_COLUMNS:
        if column.endswith("_pct"):
            typed[column] = parse_pct(row.get(column))
        elif column in INTEGER_COLUMNS:
            typed[column] = parse_count(row.get(column))
        else:
            raise AssertionError(f"Unhandled player stat column: {column}")
    if typed["appearances"] is None:
        raise ValueError(f"Player row missing appearances: {row}")
    return typed


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    corrections = load_corrections()

    report: dict[str, object] = {
        "warnings": [],
        "staging_counts": {},
        "final_counts": {},
        "skipped_player_club_rows": Counter(),
    }

    match_rows = read_csv(MATCH_FILE)
    write_csv(
        PROCESSED / "staging_match_raw.csv",
        [
            {
                "season": row["Season"],
                "match_date": row["MatchDate"],
                "home_team": row["HomeTeam"],
                "away_team": row["AwayTeam"],
                "full_time_home_goals": row["FullTimeHomeGoals"],
                "full_time_away_goals": row["FullTimeAwayGoals"],
                "full_time_result": row["FullTimeResult"],
                "half_time_home_goals": row["HalfTimeHomeGoals"],
                "half_time_away_goals": row["HalfTimeAwayGoals"],
                "half_time_result": row["HalfTimeResult"],
                "home_shots": row["HomeShots"],
                "away_shots": row["AwayShots"],
                "home_shots_on_target": row["HomeShotsOnTarget"],
                "away_shots_on_target": row["AwayShotsOnTarget"],
                "home_corners": row["HomeCorners"],
                "away_corners": row["AwayCorners"],
                "home_fouls": row["HomeFouls"],
                "away_fouls": row["AwayFouls"],
                "home_yellow_cards": row["HomeYellowCards"],
                "away_yellow_cards": row["AwayYellowCards"],
                "home_red_cards": row["HomeRedCards"],
                "away_red_cards": row["AwayRedCards"],
            }
            for row in match_rows
        ],
        [
            "season",
            "match_date",
            "home_team",
            "away_team",
            "full_time_home_goals",
            "full_time_away_goals",
            "full_time_result",
            "half_time_home_goals",
            "half_time_away_goals",
            "half_time_result",
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_corners",
            "away_corners",
            "home_fouls",
            "away_fouls",
            "home_yellow_cards",
            "away_yellow_cards",
            "home_red_cards",
            "away_red_cards",
        ],
    )
    report["staging_counts"]["staging_match_raw"] = len(match_rows)

    player_staging_rows: list[dict[str, str]] = []
    for path in PLAYER_FILES:
        season_name = season_from_player_file(path)
        for row in read_csv(path):
            player_staging_rows.append(clean_player_raw_row(path, season_name, row))
    write_csv(PROCESSED / "staging_player_stats_raw.csv", player_staging_rows, STAGING_PLAYER_COLUMNS)
    report["staging_counts"]["staging_player_stats_raw"] = len(player_staging_rows)

    player_club_rows = read_csv(PLAYER_CLUB_FILE)
    write_csv(
        PROCESSED / "staging_player_club_raw.csv",
        [
            {
                "source_player_code": row["player_id"],
                "source_club_code": row["club_id"],
                "source_season": row["season"],
                "source_player_name": row["player_name"],
                "source_club_name": row["club_name"],
            }
            for row in player_club_rows
        ],
        [
            "source_player_code",
            "source_club_code",
            "source_season",
            "source_player_name",
            "source_club_name",
        ],
    )
    report["staging_counts"]["staging_player_club_raw"] = len(player_club_rows)

    season_rows = []
    season_id_by_name = {}
    for index, season_name in enumerate(TARGET_SEASONS, start=1):
        start_year, end_year = season_years(season_name)
        season_id_by_name[season_name] = index
        season_rows.append(
            {
                "season_id": index,
                "season_name": season_name,
                "start_year": start_year,
                "end_year": end_year,
            }
        )
    write_csv(PROCESSED / "season.csv", season_rows, ["season_id", "season_name", "start_year", "end_year"])

    correction_log = []
    target_match_rows = []
    for row in match_rows:
        if row["Season"] not in TARGET_SEASONS:
            continue
        row = dict(row)
        for correction in corrections.get("match_stat_corrections", []):
            if (
                row["Season"] == correction["season"]
                and row["MatchDate"] == correction["match_date"]
                and row["HomeTeam"] == correction["home_team"]
                and row["AwayTeam"] == correction["away_team"]
                and row[correction["field"]] == correction["raw_value"]
            ):
                row[correction["field"]] = correction["corrected_value"]
                correction_log.append(correction)
        target_match_rows.append(row)
    canonical_teams = sorted(
        {clean_team_name(row["HomeTeam"]) for row in target_match_rows}
        | {clean_team_name(row["AwayTeam"]) for row in target_match_rows}
    )
    team_id_by_name = {name: index for index, name in enumerate(canonical_teams, start=1)}
    team_rows = [{"team_id": team_id, "team_name": name} for name, team_id in team_id_by_name.items()]
    write_csv(PROCESSED / "team.csv", team_rows, ["team_id", "team_name"])

    positions = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
    position_id_by_name = {name: index for index, name in enumerate(positions, start=1)}
    write_csv(
        PROCESSED / "position.csv",
        [{"position_id": position_id_by_name[name], "position_name": name} for name in positions],
        ["position_id", "position_name"],
    )

    deduped_player_stat_rows: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_player_stat_rows = []
    conflicting_player_stat_rows = []
    rejected_keys = {
        (normalize_player_name(row["name"]), row["season_name"], row["source_file"])
        for row in corrections.get("rejected_player_stat_rows", [])
    }
    rejected_player_stat_rows = []
    for row in player_staging_rows:
        if row["season_name"] not in TARGET_SEASONS:
            continue
        player_name = normalize_space(row["player_name"])
        if not player_name:
            report["warnings"].append(f"Skipped player stat row with blank player name in {row['source_file']}")
            continue
        normalized = normalize_player_name(player_name)
        if (normalized, row["season_name"], row["source_file"]) in rejected_keys:
            rejected_player_stat_rows.append(row)
            continue
        key = (normalized, row["season_name"])
        comparable = {k: v for k, v in row.items() if k != "source_file"}
        if key in deduped_player_stat_rows:
            existing = {k: v for k, v in deduped_player_stat_rows[key].items() if k != "source_file"}
            if comparable == existing:
                duplicate_player_stat_rows.append(row)
            else:
                conflicting_player_stat_rows.append({"existing": deduped_player_stat_rows[key], "incoming": row})
            continue
        deduped_player_stat_rows[key] = row
    if conflicting_player_stat_rows:
        raise RuntimeError(
            "Conflicting player-season rows found. See data/reports/conflicting_player_stat_rows.json"
        )

    (REPORTS / "duplicate_player_stat_rows.json").write_text(
        json.dumps(duplicate_player_stat_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report["duplicate_player_stat_rows_removed"] = len(duplicate_player_stat_rows)
    (REPORTS / "rejected_player_stat_rows.json").write_text(
        json.dumps(rejected_player_stat_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (REPORTS / "manual_correction_log.json").write_text(
        json.dumps(correction_log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report["rejected_player_stat_rows"] = len(rejected_player_stat_rows)
    report["manual_match_stat_corrections"] = len(correction_log)

    player_display_by_norm: dict[str, str] = {}
    for normalized, _season in sorted(deduped_player_stat_rows):
        player_display_by_norm.setdefault(normalized, normalize_space(deduped_player_stat_rows[(normalized, _season)]["player_name"]))
    player_id_by_norm = {normalized: index for index, normalized in enumerate(sorted(player_display_by_norm), start=1)}
    player_rows = [
        {
            "player_id": player_id_by_norm[normalized],
            "player_name": player_display_by_norm[normalized],
            "normalized_player_name": normalized,
        }
        for normalized in sorted(player_display_by_norm)
    ]
    write_csv(PROCESSED / "player.csv", player_rows, ["player_id", "player_name", "normalized_player_name"])

    match_final_rows = []
    match_team_stats_rows = []
    for match_id, row in enumerate(target_match_rows, start=1):
        home_team = clean_team_name(row["HomeTeam"])
        away_team = clean_team_name(row["AwayTeam"])
        final_match = {
            "match_id": match_id,
            "season_id": season_id_by_name[row["Season"]],
            "match_date": row["MatchDate"],
            "home_team_id": team_id_by_name[home_team],
            "away_team_id": team_id_by_name[away_team],
            "full_time_home_goals": parse_int(row["FullTimeHomeGoals"]),
            "full_time_away_goals": parse_int(row["FullTimeAwayGoals"]),
            "full_time_result": row["FullTimeResult"],
            "half_time_home_goals": parse_int(row["HalfTimeHomeGoals"]),
            "half_time_away_goals": parse_int(row["HalfTimeAwayGoals"]),
            "half_time_result": row["HalfTimeResult"],
        }
        match_final_rows.append(final_match)
        match_team_stats_rows.append(
            {
                "match_id": match_id,
                "team_id": team_id_by_name[home_team],
                "is_home": "true",
                "goals": final_match["full_time_home_goals"],
                "shots": parse_int(row["HomeShots"]),
                "shots_on_target": parse_int(row["HomeShotsOnTarget"]),
                "corners": parse_int(row["HomeCorners"]),
                "fouls": parse_int(row["HomeFouls"]),
                "yellow_cards": parse_int(row["HomeYellowCards"]),
                "red_cards": parse_int(row["HomeRedCards"]),
            }
        )
        match_team_stats_rows.append(
            {
                "match_id": match_id,
                "team_id": team_id_by_name[away_team],
                "is_home": "false",
                "goals": final_match["full_time_away_goals"],
                "shots": parse_int(row["AwayShots"]),
                "shots_on_target": parse_int(row["AwayShotsOnTarget"]),
                "corners": parse_int(row["AwayCorners"]),
                "fouls": parse_int(row["AwayFouls"]),
                "yellow_cards": parse_int(row["AwayYellowCards"]),
                "red_cards": parse_int(row["AwayRedCards"]),
            }
        )
    write_csv(
        PROCESSED / "match_record.csv",
        match_final_rows,
        [
            "match_id",
            "season_id",
            "match_date",
            "home_team_id",
            "away_team_id",
            "full_time_home_goals",
            "full_time_away_goals",
            "full_time_result",
            "half_time_home_goals",
            "half_time_away_goals",
            "half_time_result",
        ],
    )
    write_csv(
        PROCESSED / "match_team_stats.csv",
        match_team_stats_rows,
        [
            "match_id",
            "team_id",
            "is_home",
            "goals",
            "shots",
            "shots_on_target",
            "corners",
            "fouls",
            "yellow_cards",
            "red_cards",
        ],
    )

    player_team_seen = set()
    player_team_rows = []
    skipped_player_club_rows = []
    for row in player_club_rows:
        season_name = full_source_season_to_short(row["season"])
        if season_name not in TARGET_SEASONS:
            report["skipped_player_club_rows"]["season_out_of_scope"] += 1
            continue
        source_player_name = normalize_space(row["player_name"])
        normalized = normalize_player_name(source_player_name)
        if normalized not in player_id_by_norm:
            report["skipped_player_club_rows"]["player_not_in_stats_dataset"] += 1
            skipped_player_club_rows.append(row)
            continue
        team_name = clean_team_name(row["club_name"])
        if team_name not in team_id_by_name:
            report["skipped_player_club_rows"]["club_not_in_match_dataset"] += 1
            skipped_player_club_rows.append(row)
            continue
        key = (player_id_by_norm[normalized], season_id_by_name[season_name], team_id_by_name[team_name])
        if key in player_team_seen:
            report["skipped_player_club_rows"]["duplicate_membership"] += 1
            continue
        player_team_seen.add(key)
        player_team_rows.append(
            {
                "player_id": key[0],
                "season_id": key[1],
                "team_id": key[2],
                "source_player_code": row["player_id"],
                "source_player_name": source_player_name,
            }
        )
    write_csv(
        PROCESSED / "player_team_season.csv",
        player_team_rows,
        ["player_id", "season_id", "team_id", "source_player_code", "source_player_name"],
    )
    (REPORTS / "skipped_player_club_rows.json").write_text(
        json.dumps(skipped_player_club_rows[:500], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    mapped_player_seasons = {
        (row["player_id"], row["season_id"]) for row in player_team_rows
    }
    player_season_rows = []
    dropped_unmapped_player_stat_rows = []
    for (normalized, season_name), row in sorted(deduped_player_stat_rows.items()):
        player_id = player_id_by_norm[normalized]
        season_id = season_id_by_name[season_name]
        if (player_id, season_id) not in mapped_player_seasons:
            dropped_unmapped_player_stat_rows.append(row)
            continue
        position_name = normalize_space(row["position_name"])
        if position_name not in position_id_by_name:
            raise ValueError(f"Unknown position {position_name!r} in player row {row}")
        typed_stats = typed_player_stat_row(row)
        player_season_rows.append(
            {
                "player_season_stats_id": len(player_season_rows) + 1,
                "player_id": player_id,
                "season_id": season_id,
                "position_id": position_id_by_name[position_name],
                **typed_stats,
            }
        )
    write_csv(
        PROCESSED / "player_season_stats.csv",
        player_season_rows,
        ["player_season_stats_id", "player_id", "season_id", "position_id", *PLAYER_FINAL_STAT_COLUMNS],
    )
    (REPORTS / "dropped_unmapped_player_stat_rows.json").write_text(
        json.dumps(dropped_unmapped_player_stat_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report["dropped_unmapped_player_stat_rows"] = len(dropped_unmapped_player_stat_rows)

    report["final_counts"] = {
        "season": len(season_rows),
        "team": len(team_rows),
        "position": len(positions),
        "player": len(player_rows),
        "match_record": len(match_final_rows),
        "match_team_stats": len(match_team_stats_rows),
        "player_season_stats": len(player_season_rows),
        "player_team_season": len(player_team_rows),
    }
    report["skipped_player_club_rows"] = dict(report["skipped_player_club_rows"])
    report["target_seasons"] = TARGET_SEASONS
    report["source_limitation"] = (
        "Final relational scope is limited to 2015/16 through 2021/22 because "
        "teammate_dump/pl_player.csv does not provide club memberships after 2021/22."
    )

    # Python-side integrity checks mirroring the SQL validation file.
    match_team_count = Counter(row["match_id"] for row in match_team_stats_rows)
    report["validation"] = {
        "matches_without_two_team_rows": sum(1 for count in match_team_count.values() if count != 2),
        "duplicate_player_season_rows": len(player_season_rows)
        - len({(row["player_id"], row["season_id"]) for row in player_season_rows}),
        "transferred_player_seasons": sum(
            1
            for count in Counter((row["player_id"], row["season_id"]) for row in player_team_rows).values()
            if count > 1
        ),
        "data_quality_team_stats_shots_on_target_gt_shots": sum(
            1 for row in match_team_stats_rows if row["shots_on_target"] > row["shots"]
        ),
        "data_quality_player_appearances_gt_38": sum(
            1 for row in player_season_rows if row["appearances"] > 38
        ),
    }
    (REPORTS / "build_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
