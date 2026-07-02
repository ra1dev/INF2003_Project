# Route handlers for the player search and player stat pages.
from flask import Blueprint, render_template, request, url_for

from Backend.db_conn import get_db
from Backend.repositories.players_repository import (
    get_player_season_stats,
    get_players,
    get_team_options,
)


players_bp = Blueprint("players", __name__)

PLAYER_STAT_CATALOG = [
    {"key": "appearances", "label": "Appearances", "group": "Core", "type": "sum"},
    {"key": "goal_contributions", "label": "Goal Contributions", "group": "Attacking", "type": "derived_sum", "fields": ["goals", "assists"]},
    {"key": "goals", "label": "Goals", "group": "Attacking", "type": "sum"},
    {"key": "assists", "label": "Assists", "group": "Attacking", "type": "sum"},
    {"key": "shots", "label": "Shots", "group": "Attacking", "type": "sum"},
    {"key": "shots_on_target", "label": "Shots On Target", "group": "Attacking", "type": "sum"},
    {"key": "shot_accuracy", "label": "Shot Accuracy", "group": "Attacking", "type": "ratio", "numerator": "shots_on_target", "denominator": "shots"},
    {"key": "goal_conversion", "label": "Goal Conversion", "group": "Attacking", "type": "ratio", "numerator": "goals", "denominator": "shots"},
    {"key": "big_chances_missed", "label": "Big Chances Missed", "group": "Attacking", "type": "sum"},
    {"key": "hit_woodwork", "label": "Hit Woodwork", "group": "Attacking", "type": "sum"},
    {"key": "big_chances_created", "label": "Big Chances Created", "group": "Creativity", "type": "sum"},
    {"key": "passes", "label": "Passes", "group": "Creativity", "type": "sum"},
    {"key": "crosses", "label": "Crosses", "group": "Creativity", "type": "sum"},
    {"key": "cross_accuracy_pct", "label": "Cross Accuracy", "group": "Creativity", "type": "average_pct"},
    {"key": "through_balls", "label": "Through Balls", "group": "Creativity", "type": "sum"},
    {"key": "accurate_long_balls", "label": "Accurate Long Balls", "group": "Creativity", "type": "sum"},
    {"key": "clean_sheets", "label": "Clean Sheets", "group": "Defending", "type": "sum"},
    {"key": "goals_conceded", "label": "Goals Conceded", "group": "Defending", "type": "sum"},
    {"key": "tackles", "label": "Tackles", "group": "Defending", "type": "sum"},
    {"key": "tackle_success_pct", "label": "Tackle Success", "group": "Defending", "type": "average_pct"},
    {"key": "interceptions", "label": "Interceptions", "group": "Defending", "type": "sum"},
    {"key": "clearances", "label": "Clearances", "group": "Defending", "type": "sum"},
    {"key": "blocked_shots", "label": "Blocked Shots", "group": "Defending", "type": "sum"},
    {"key": "recoveries", "label": "Recoveries", "group": "Defending", "type": "sum"},
    {"key": "duels_won", "label": "Duels Won", "group": "Duels", "type": "sum"},
    {"key": "duel_success", "label": "Duel Success", "group": "Duels", "type": "ratio", "numerator": "duels_won", "denominator_fields": ["duels_won", "duels_lost"]},
    {"key": "aerial_battles_won", "label": "Aerial Battles Won", "group": "Duels", "type": "sum"},
    {"key": "aerial_success", "label": "Aerial Success", "group": "Duels", "type": "ratio", "numerator": "aerial_battles_won", "denominator_fields": ["aerial_battles_won", "aerial_battles_lost"]},
    {"key": "yellow_cards", "label": "Yellow Cards", "group": "Discipline", "type": "sum"},
    {"key": "red_cards", "label": "Red Cards", "group": "Discipline", "type": "sum"},
    {"key": "fouls", "label": "Fouls", "group": "Discipline", "type": "sum"},
    {"key": "offsides", "label": "Offsides", "group": "Discipline", "type": "sum"},
    {"key": "saves", "label": "Saves", "group": "Goalkeeping", "type": "sum"},
    {"key": "penalties_saved", "label": "Penalties Saved", "group": "Goalkeeping", "type": "sum"},
    {"key": "high_claims", "label": "High Claims", "group": "Goalkeeping", "type": "sum"},
    {"key": "catches", "label": "Catches", "group": "Goalkeeping", "type": "sum"},
    {"key": "sweeper_clearances", "label": "Sweeper Clearances", "group": "Goalkeeping", "type": "sum"},
]

DEFAULT_PLAYER_STATS = {
    "goalkeeper": ["appearances", "clean_sheets", "saves", "goals_conceded", "penalties_saved", "high_claims", "yellow_cards", "red_cards"],
    "defender": ["appearances", "clean_sheets", "tackles", "tackle_success_pct", "interceptions", "clearances", "yellow_cards", "red_cards"],
    "midfielder": ["appearances", "goal_contributions", "assists", "big_chances_created", "passes", "recoveries", "yellow_cards", "red_cards"],
    "forward": ["appearances", "goal_contributions", "goals", "assists", "shots_on_target", "shot_accuracy", "yellow_cards", "red_cards"],
    "default": ["appearances", "goal_contributions", "goals", "assists", "shot_accuracy", "big_chances_created", "yellow_cards", "red_cards"],
}


def position_bucket(position_name):
    position = (position_name or "").lower()
    for bucket in ("goalkeeper", "defender", "midfielder", "forward"):
        if bucket in position:
            return bucket
    return "default"


def format_stat_value(value, is_percent=False):
    if value is None:
        return "-"
    if is_percent:
        return f"{value:.1f}%"
    return int(value) if value == int(value) else round(value, 1)


def build_player_stats(rows, default_keys):
    stat_cards = []

    for stat in PLAYER_STAT_CATALOG:
        stat_type = stat["type"]
        is_percent = stat_type in ("ratio", "average_pct")

        if stat_type == "sum":
            value = sum(row[stat["key"]] or 0 for row in rows)
        elif stat_type == "derived_sum":
            value = sum(sum(row[field] or 0 for field in stat["fields"]) for row in rows)
        elif stat_type == "average_pct":
            values = [row[stat["key"]] for row in rows if row[stat["key"]] is not None]
            value = sum(values) / len(values) if values else None
        elif stat_type == "ratio":
            numerator = sum(row[stat["numerator"]] or 0 for row in rows)
            denominator_fields = stat.get("denominator_fields", [stat.get("denominator")])
            denominator = sum(
                sum(row[field] or 0 for field in denominator_fields)
                for row in rows
            )
            value = (numerator / denominator * 100) if denominator else None
        else:
            value = None

        stat_cards.append({
            "key": stat["key"],
            "label": stat["label"],
            "group": stat["group"],
            "value": format_stat_value(value, is_percent),
            "selected": stat["key"] in default_keys,
        })

    return stat_cards


def group_player_stats(stat_cards):
    grouped_stats = []
    groups = ["Core", "Attacking", "Creativity", "Defending", "Duels", "Discipline", "Goalkeeping"]

    for group_name in groups:
        group_cards = [
            stat for stat in stat_cards
            if stat["group"] == group_name and not stat["selected"]
        ]
        if group_cards:
            grouped_stats.append({"name": group_name, "stats": group_cards})

    return grouped_stats


@players_bp.route("/players")
def players_page():
    search = request.args.get("search")
    team = request.args.get("team")
    conn = get_db()

    return render_template(
        "players.html",
        title="Players",
        players=get_players(conn, search, team),
        teams=get_team_options(conn),
        search=search,
        selected_team=team,
    )


@players_bp.route("/player/<int:player_id>")
def player_detail(player_id):
    selected_season = request.args.get("season", "combined")
    stats = get_player_season_stats(get_db(), player_id)
    player = None

    if stats:
        seasons = [row["season_name"] for row in stats]
        view_stats = stats

        if selected_season != "combined":
            view_stats = [row for row in stats if row["season_name"] == selected_season]

        if not view_stats:
            selected_season = "combined"
            view_stats = stats

        image_url = (
            stats[0]["player_image"]
            or stats[0]["player_photo_url"]
            or url_for("static", filename="images/player-placeholder.png")
        )
        latest_view_row = view_stats[-1]
        position_name = latest_view_row["position_name"]
        position_key = position_bucket(position_name)
        default_stat_keys = DEFAULT_PLAYER_STATS[position_key]
        stat_cards = build_player_stats(view_stats, default_stat_keys)

        player = {
            "player_id": stats[0]["player_id"],
            "player_name": stats[0]["player_name"],
            "team_name": latest_view_row["team_name"] or "Unknown Team",
            "team_logo": latest_view_row["team_logo"],
            "position_name": position_name,
            "image_url": image_url,
            "stat_cards": stat_cards,
            "available_stat_groups": group_player_stats(stat_cards),
            "default_stat_keys": default_stat_keys,
            "preset_stats": DEFAULT_PLAYER_STATS,
            "position_key": position_key,
            "selected_season": selected_season,
            "seasons": seasons,
            "is_combined_view": selected_season == "combined",
        }

    return render_template(
        "player_detail.html",
        title="Player Stats",
        player=player,
        stats=stats,
        selected_season=selected_season,
    )
