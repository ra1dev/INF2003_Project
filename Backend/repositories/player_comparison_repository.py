# Repository helpers for the player comparison and stat-selection experience.
from flask import render_template, request, url_for
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


PLAYER_STAT_FIELDS = [
    "appearances",
    "clean_sheets",
    "goals_conceded",
    "tackles",
    "tackle_success_pct",
    "blocked_shots",
    "interceptions",
    "clearances",
    "recoveries",
    "duels_won",
    "duels_lost",
    "aerial_battles_won",
    "aerial_battles_lost",
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
]

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

    if "goalkeeper" in position:
        return "goalkeeper"
    if "defender" in position:
        return "defender"
    if "midfielder" in position:
        return "midfielder"
    if "forward" in position:
        return "forward"
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
            value = sum(
                sum(row[field] or 0 for field in stat["fields"])
                for row in rows
            )
        elif stat_type == "average_pct":
            values = [row[stat["key"]] for row in rows if row[stat["key"]] is not None]
            value = sum(values) / len(values) if values else None
        elif stat_type == "ratio":
            numerator = sum(row[stat["numerator"]] or 0 for row in rows)
            if "denominator_fields" in stat:
                denominator = sum(
                    sum(row[field] or 0 for field in stat["denominator_fields"])
                    for row in rows
                )
            else:
                denominator = sum(row[stat["denominator"]] or 0 for row in rows)
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

    for group_name in ["Core", "Attacking", "Creativity", "Defending", "Duels", "Discipline", "Goalkeeping"]:
        group_cards = [
            stat for stat in stat_cards
            if stat["group"] == group_name and not stat["selected"]
        ]

        if group_cards:
            grouped_stats.append({
                "name": group_name,
                "stats": group_cards,
            })

    return grouped_stats


TEAM_COMPARISON_GROUPS = [
    {
        "title": "Context",
        "metrics": [
            {"key": "seasons_played", "label": "Seasons Played", "format": "integer", "winner": "neutral"},
            {"key": "matches_played", "label": "Matches Played", "format": "integer", "winner": "neutral"},
        ],
    },
    {
        "title": "League Rank Context",
        "metrics": [
            {"key": "average_league_position", "label": "Avg League Position", "format": "rank", "winner": "lower"},
            {"key": "best_league_position", "label": "Best League Finish", "format": "rank", "winner": "lower"},
            {"key": "worst_league_position", "label": "Worst League Finish", "format": "rank", "winner": "lower"},
            {"key": "average_attack_rank", "label": "Avg Attack Rank", "format": "rank", "winner": "lower"},
            {"key": "average_defense_rank", "label": "Avg Defence Rank", "format": "rank", "winner": "lower"},
            {"key": "average_pressure_rank", "label": "Avg Pressure Rank", "format": "rank", "winner": "lower"},
            {"key": "average_home_rank", "label": "Avg Home Rank", "format": "rank", "winner": "lower"},
            {"key": "average_away_rank", "label": "Avg Away Rank", "format": "rank", "winner": "lower"},
            {"key": "average_discipline_rank", "label": "Avg Discipline Rank", "format": "rank", "winner": "lower"},
        ],
    },
    {
        "title": "Overall Record",
        "metrics": [
            {"key": "wins", "label": "Wins", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "draws", "label": "Draws", "format": "integer", "winner": "neutral"},
            {"key": "losses", "label": "Losses", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "points", "label": "Points", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "points_per_match", "label": "Points Per Match", "format": "decimal", "winner": "higher"},
            {"key": "win_rate_pct", "label": "Win Rate", "format": "percent", "winner": "higher"},
            {"key": "goal_difference", "label": "Goal Difference", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "goal_difference_per_match", "label": "Goal Difference Per Match", "format": "decimal", "winner": "higher"},
        ],
    },
    {
        "title": "Attacking Efficiency",
        "metrics": [
            {"key": "goals_for", "label": "Goals", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "goals_per_match", "label": "Goals Per Match", "format": "decimal", "winner": "higher"},
            {"key": "shots", "label": "Shots", "format": "integer", "winner": "neutral"},
            {"key": "shots_per_match", "label": "Shots Per Match", "format": "decimal", "winner": "higher"},
            {"key": "shots_on_target", "label": "Shots On Target", "format": "integer", "winner": "neutral"},
            {"key": "shots_on_target_per_match", "label": "Shots On Target Per Match", "format": "decimal", "winner": "higher"},
            {"key": "shot_accuracy_pct", "label": "Shot Accuracy", "format": "percent", "winner": "higher"},
            {"key": "goal_conversion_pct", "label": "Goal Conversion", "format": "percent", "winner": "higher"},
            {"key": "goal_share_pct", "label": "Goal Share", "format": "percent", "winner": "higher"},
        ],
    },
    {
        "title": "Opponent Pressure",
        "metrics": [
            {"key": "shots_allowed_per_match", "label": "Shots Allowed Per Match", "format": "decimal", "winner": "lower"},
            {"key": "shot_difference_per_match", "label": "Shot Difference Per Match", "format": "decimal", "winner": "higher"},
            {"key": "shots_on_target_allowed_per_match", "label": "Shots On Target Allowed Per Match", "format": "decimal", "winner": "lower"},
            {"key": "shots_on_target_difference_per_match", "label": "SOT Difference Per Match", "format": "decimal", "winner": "higher"},
            {"key": "shot_share_pct", "label": "Shot Share", "format": "percent", "winner": "higher"},
            {"key": "shot_on_target_share_pct", "label": "SOT Share", "format": "percent", "winner": "higher"},
            {"key": "corners_per_match", "label": "Corners Per Match", "format": "decimal", "winner": "higher"},
            {"key": "corners_allowed_per_match", "label": "Corners Allowed Per Match", "format": "decimal", "winner": "lower"},
            {"key": "corner_difference_per_match", "label": "Corner Difference Per Match", "format": "decimal", "winner": "higher"},
            {"key": "corner_share_pct", "label": "Corner Share", "format": "percent", "winner": "higher"},
        ],
    },
    {
        "title": "Defensive Strength",
        "metrics": [
            {"key": "goals_against", "label": "Goals Conceded", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "goals_conceded_per_match", "label": "Goals Conceded Per Match", "format": "decimal", "winner": "lower"},
            {"key": "clean_sheets", "label": "Clean Sheets", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "clean_sheet_rate_pct", "label": "Clean Sheet Rate", "format": "percent", "winner": "higher"},
            {"key": "failed_to_score", "label": "Failed To Score", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "failed_to_score_rate_pct", "label": "Failed To Score Rate", "format": "percent", "winner": "lower"},
        ],
    },
    {
        "title": "Home vs Away",
        "metrics": [
            {"key": "home_matches", "label": "Home Matches", "format": "integer", "winner": "neutral"},
            {"key": "home_points", "label": "Home Points", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "home_points_per_match", "label": "Home Points Per Match", "format": "decimal", "winner": "higher"},
            {"key": "home_win_rate_pct", "label": "Home Win Rate", "format": "percent", "winner": "higher"},
            {"key": "away_matches", "label": "Away Matches", "format": "integer", "winner": "neutral"},
            {"key": "away_points", "label": "Away Points", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "away_points_per_match", "label": "Away Points Per Match", "format": "decimal", "winner": "higher"},
            {"key": "away_win_rate_pct", "label": "Away Win Rate", "format": "percent", "winner": "higher"},
        ],
    },
    {
        "title": "Discipline",
        "metrics": [
            {"key": "fouls", "label": "Fouls", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "fouls_per_match", "label": "Fouls Per Match", "format": "decimal", "winner": "lower"},
            {"key": "yellow_cards", "label": "Yellow Cards", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "red_cards", "label": "Red Cards", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "cards", "label": "Total Cards", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "cards_per_match", "label": "Cards Per Match", "format": "decimal", "winner": "lower"},
            {"key": "discipline_score", "label": "Discipline Score", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "discipline_score_per_match", "label": "Discipline Score Per Match", "format": "decimal", "winner": "lower"},
        ],
    },
]


TEAM_METRIC_DESCRIPTIONS = {
    "average_league_position": "Average final league-table position across the selected seasons. Lower is better.",
    "best_league_position": "Best final league-table position reached in the selected seasons.",
    "worst_league_position": "Lowest final league-table position reached in the selected seasons.",
    "average_attack_rank": "Average seasonal rank by goals per match, goal conversion, and shots on target per match. Lower is better.",
    "average_defense_rank": "Average seasonal rank by goals conceded per match, clean sheet rate, and shots on target allowed. Lower is better.",
    "average_pressure_rank": "Average seasonal rank by shot share, shot difference, and shots per match. Lower is better.",
    "average_home_rank": "Average seasonal rank by home points per match and home win rate. Lower is better.",
    "average_away_rank": "Average seasonal rank by away points per match and away win rate. Lower is better.",
    "average_discipline_rank": "Average seasonal rank by discipline score per match. Lower is cleaner.",
    "points_per_match": "Total points divided by matches played.",
    "win_rate_pct": "Wins divided by matches played.",
    "goal_difference_per_match": "Goal difference divided by matches played.",
    "goals_per_match": "Goals scored divided by matches played.",
    "shots_per_match": "Shots taken divided by matches played.",
    "shots_on_target_per_match": "Shots on target divided by matches played.",
    "shot_accuracy_pct": "Shots on target divided by total shots.",
    "goal_conversion_pct": "Goals scored divided by total shots.",
    "goal_share_pct": "Team goals divided by all goals in that team's matches.",
    "shots_allowed_per_match": "Opponent shots divided by matches played.",
    "shot_difference_per_match": "Team shots minus opponent shots, divided by matches played.",
    "shots_on_target_allowed_per_match": "Opponent shots on target divided by matches played.",
    "shots_on_target_difference_per_match": "Team shots on target minus opponent shots on target, divided by matches played.",
    "shot_share_pct": "Team shots divided by total shots by both teams in those matches.",
    "shot_on_target_share_pct": "Team shots on target divided by total shots on target by both teams.",
    "corners_per_match": "Corners won divided by matches played.",
    "corners_allowed_per_match": "Opponent corners divided by matches played.",
    "corner_difference_per_match": "Team corners minus opponent corners, divided by matches played.",
    "corner_share_pct": "Team corners divided by total corners by both teams.",
    "goals_conceded_per_match": "Goals conceded divided by matches played.",
    "clean_sheet_rate_pct": "Clean sheets divided by matches played.",
    "failed_to_score_rate_pct": "Matches without scoring divided by matches played.",
    "home_points_per_match": "Home points divided by home matches played.",
    "home_win_rate_pct": "Home wins divided by home matches played.",
    "away_points_per_match": "Away points divided by away matches played.",
    "away_win_rate_pct": "Away wins divided by away matches played.",
    "fouls_per_match": "Fouls committed divided by matches played.",
    "cards_per_match": "Yellow cards plus red cards, divided by matches played.",
    "discipline_score": "Yellow cards plus three times red cards.",
    "discipline_score_per_match": "Discipline score divided by matches played. Lower is cleaner.",
}


def format_team_metric(value, format_type):
    if value is None:
        return "-"

    if format_type == "percent":
        return f"{float(value):.2f}%"

    if format_type == "decimal":
        return f"{float(value):.2f}"

    if format_type == "rank":
        rank_value = float(value)
        if rank_value.is_integer():
            return f"#{int(rank_value)}"
        return f"#{rank_value:.2f}"

    return f"{int(value)}"


def metric_winner(metric, team_a, team_b, neutralize_raw_totals):
    winner_rule = metric.get("all_time_winner", metric["winner"]) if neutralize_raw_totals else metric["winner"]

    if winner_rule == "neutral":
        return None

    a_value = team_a.get(metric["key"])
    b_value = team_b.get(metric["key"])

    if a_value is None or b_value is None or a_value == b_value:
        return None

    if winner_rule == "lower":
        return "a" if a_value < b_value else "b"

    return "a" if a_value > b_value else "b"


def build_team_comparison_sections(team_a, team_b, neutralize_raw_totals):
    sections = []

    for group in TEAM_COMPARISON_GROUPS:
        rows = []

        for metric in group["metrics"]:
            winner = metric_winner(metric, team_a, team_b, neutralize_raw_totals)
            rows.append({
                "label": metric["label"],
                "description": metric.get("description") or TEAM_METRIC_DESCRIPTIONS.get(metric["key"]),
                "a_value": format_team_metric(team_a.get(metric["key"]), metric["format"]),
                "b_value": format_team_metric(team_b.get(metric["key"]), metric["format"]),
                "winner": winner,
            })

        sections.append({
            "title": group["title"],
            "rows": rows,
        })

    return sections


def chart_number(value):
    return None if value is None else float(value)


def format_rank_summary(value):
    if value is None:
        return "-"

    value = float(value)
    if value.is_integer():
        return f"#{int(value)}"
    return f"#{value:.2f}"


def build_team_season_highlights(rows):
    if not rows:
        return []

    best_points = max(rows, key=lambda row: (row["points"] or 0, row["goal_difference"] or 0))
    worst_points = min(rows, key=lambda row: (row["points"] or 0, row["goal_difference"] or 0))
    best_finish = min(rows, key=lambda row: (row["league_position"] or 999, -(row["points"] or 0)))
    worst_finish = max(rows, key=lambda row: (row["league_position"] or 0, -(row["points"] or 0)))
    best_attack = min(rows, key=lambda row: (row["attack_rank"] or 999, -(row["goals_per_match"] or 0)))
    best_defense = min(rows, key=lambda row: (row["defense_rank"] or 999, row["goals_conceded_per_match"] or 999))

    return [
        {
            "label": "Best Points Season",
            "season": best_points["season_name"],
            "value": f"{best_points['points']} pts",
            "detail": f"{format_rank_summary(best_points['league_position'])} league finish",
        },
        {
            "label": "Worst Points Season",
            "season": worst_points["season_name"],
            "value": f"{worst_points['points']} pts",
            "detail": f"{format_rank_summary(worst_points['league_position'])} league finish",
        },
        {
            "label": "Best League Finish",
            "season": best_finish["season_name"],
            "value": format_rank_summary(best_finish["league_position"]),
            "detail": f"{best_finish['points']} pts",
        },
        {
            "label": "Best Attack Season",
            "season": best_attack["season_name"],
            "value": format_rank_summary(best_attack["attack_rank"]),
            "detail": f"{best_attack['goals_per_match']} goals per match",
        },
        {
            "label": "Best Defence Season",
            "season": best_defense["season_name"],
            "value": format_rank_summary(best_defense["defense_rank"]),
            "detail": f"{best_defense['goals_conceded_per_match']} conceded per match",
        },
        {
            "label": "Worst League Finish",
            "season": worst_finish["season_name"],
            "value": format_rank_summary(worst_finish["league_position"]),
            "detail": f"{worst_finish['points']} pts",
        },
    ]


def build_team_trend_data(rows, team_a, team_b):
    season_axis = []
    seen_seasons = set()

    for row in rows:
        if row["season_id"] not in seen_seasons:
            seen_seasons.add(row["season_id"])
            season_axis.append({
                "season_id": row["season_id"],
                "season_name": row["season_name"],
            })

    rows_by_team_and_season = {
        (row["team_id"], row["season_id"]): row
        for row in rows
    }

    metrics = [
        {"key": "points_per_match", "label": "Points Per Match"},
        {"key": "goals_per_match", "label": "Goals Per Match"},
        {"key": "goals_conceded_per_match", "label": "Goals Conceded Per Match"},
        {"key": "win_rate_pct", "label": "Win Rate %"},
        {"key": "goal_difference_per_match", "label": "Goal Difference Per Match"},
    ]

    charts = []
    for metric in metrics:
        charts.append({
            "key": metric["key"],
            "label": metric["label"],
            "labels": [season["season_name"] for season in season_axis],
            "team_a_name": team_a["team_name"],
            "team_b_name": team_b["team_name"],
            "team_a_values": [
                chart_number(rows_by_team_and_season.get((team_a["team_id"], season["season_id"]), {}).get(metric["key"]))
                for season in season_axis
            ],
            "team_b_values": [
                chart_number(rows_by_team_and_season.get((team_b["team_id"], season["season_id"]), {}).get(metric["key"]))
                for season in season_axis
            ],
        })

    return charts


def number_or_none(value):
    return None if value is None else float(value)


def team_metric_sentence(team_a, team_b, key, label, higher_is_better=True, suffix="", decimals=2, threshold=0):
    a_value = number_or_none(team_a.get(key))
    b_value = number_or_none(team_b.get(key))

    if a_value is None or b_value is None or abs(a_value - b_value) <= threshold:
        return None

    a_is_better = a_value > b_value if higher_is_better else a_value < b_value
    stronger = team_a if a_is_better else team_b
    weaker = team_b if a_is_better else team_a
    stronger_value = a_value if a_is_better else b_value
    weaker_value = b_value if a_is_better else a_value

    return (
        f"{stronger['team_name']} leads on {label}, "
        f"{stronger_value:.{decimals}f}{suffix} compared with "
        f"{weaker_value:.{decimals}f}{suffix} for {weaker['team_name']}."
    )


def rank_sentence(team_a, team_b, key, label):
    a_value = number_or_none(team_a.get(key))
    b_value = number_or_none(team_b.get(key))

    if a_value is None or b_value is None or a_value == b_value:
        return None

    stronger = team_a if a_value < b_value else team_b
    weaker = team_b if a_value < b_value else team_a
    stronger_value = a_value if a_value < b_value else b_value
    weaker_value = b_value if a_value < b_value else a_value

    return (
        f"{stronger['team_name']} has the better {label}, "
        f"{format_rank_summary(stronger_value)} versus {format_rank_summary(weaker_value)} "
        f"for {weaker['team_name']}."
    )


def build_team_comparison_insights(team_a, team_b, is_all_time, comparison_basis, head_to_head):
    insights = []

    if is_all_time and comparison_basis == "available" and team_a["seasons_played"] != team_b["seasons_played"]:
        insights.append(
            f"{team_a['team_name']} has {team_a['seasons_played']} seasons in this dataset, "
            f"while {team_b['team_name']} has {team_b['seasons_played']}; rate metrics are safer than raw totals."
        )
    elif is_all_time and comparison_basis == "common":
        insights.append(
            f"This view only compares the {team_a['seasons_played']} shared season(s), "
            "so raw totals and rates are aligned to the same coverage."
        )

    for sentence in [
        team_metric_sentence(team_a, team_b, "points_per_match", "overall points per match"),
        rank_sentence(team_a, team_b, "average_league_position", "average league-table position"),
        team_metric_sentence(team_a, team_b, "goals_per_match", "attacking output"),
        team_metric_sentence(team_a, team_b, "shot_share_pct", "shot share", suffix="%", threshold=0.25),
        team_metric_sentence(team_a, team_b, "goals_conceded_per_match", "defensive record", higher_is_better=False),
        team_metric_sentence(team_a, team_b, "discipline_score_per_match", "discipline score per match", higher_is_better=False),
    ]:
        if sentence:
            insights.append(sentence)

    if head_to_head and head_to_head["matches_played"]:
        if head_to_head["team_a_wins"] > head_to_head["team_b_wins"]:
            insights.append(
                f"In head-to-head matches, {team_a['team_name']} leads "
                f"{head_to_head['team_a_wins']}-{head_to_head['team_b_wins']} with {head_to_head['draws']} draw(s)."
            )
        elif head_to_head["team_b_wins"] > head_to_head["team_a_wins"]:
            insights.append(
                f"In head-to-head matches, {team_b['team_name']} leads "
                f"{head_to_head['team_b_wins']}-{head_to_head['team_a_wins']} with {head_to_head['draws']} draw(s)."
            )
        else:
            insights.append(
                f"The head-to-head record is level at {head_to_head['team_a_wins']} win(s) each, "
                f"with {head_to_head['draws']} draw(s)."
            )

    return insights[:6]


PLAYER_COMPARISON_METRIC_DESCRIPTIONS = {
    "seasons_played": "Number of seasons included in the selected comparison scope.",
    "appearances": "Total Premier League appearances in the selected scope.",
    "clubs_represented": "Distinct clubs mapped to the player in the selected scope.",
    "goals": "Total goals. In all-available mode, rate metrics are safer when player coverage differs.",
    "assists": "Total assists. In all-available mode, rate metrics are safer when player coverage differs.",
    "goal_contributions": "Goals plus assists.",
    "goals_per_appearance": "Goals divided by appearances.",
    "assists_per_appearance": "Assists divided by appearances.",
    "goal_contributions_per_appearance": "Goals plus assists divided by appearances.",
    "cards_per_appearance": "Yellow cards plus red cards divided by appearances.",
    "appearance_rank": "Rank by appearances among eligible players in the selected scope. Lower is better.",
    "goal_contribution_rank": "Rank by total goal contributions among eligible players. Lower is better.",
    "goal_contribution_rate_rank": "Rank by goal contributions per appearance among eligible players. Lower is better.",
    "position_appearance_rank": "Rank by appearances among eligible players in the same position. Lower is better.",
    "position_role_rank": "Position-aware rank using role-specific metrics. Lower is better.",
    "shooting_accuracy_pct": "Source shooting accuracy percentage, weighted by shots when seasons are aggregated.",
    "goal_conversion_pct": "Goals divided by shots.",
    "cross_accuracy_pct": "Source cross accuracy percentage, weighted by crosses when seasons are aggregated.",
    "tackle_success_pct": "Source tackle success percentage, weighted by tackles when seasons are aggregated.",
    "cards": "Yellow cards plus red cards.",
}

PLAYER_UNIVERSAL_GROUPS = [
    {
        "title": "Context",
        "metrics": [
            {"key": "seasons_played", "label": "Seasons Played", "format": "integer", "winner": "neutral"},
            {"key": "appearances", "label": "Appearances", "format": "integer", "winner": "neutral"},
            {"key": "clubs_represented", "label": "Clubs Represented", "format": "integer", "winner": "neutral"},
        ],
    },
    {
        "title": "Universal Output",
        "metrics": [
            {"key": "goals", "label": "Goals", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "assists", "label": "Assists", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "goal_contributions", "label": "Goal Contributions", "format": "integer", "winner": "higher", "all_time_winner": "neutral"},
            {"key": "goals_per_appearance", "label": "Goals Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "assists_per_appearance", "label": "Assists Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "goal_contributions_per_appearance", "label": "Goal Contributions Per Appearance", "format": "decimal3", "winner": "higher"},
        ],
    },
    {
        "title": "Discipline",
        "metrics": [
            {"key": "yellow_cards", "label": "Yellow Cards", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "red_cards", "label": "Red Cards", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "fouls", "label": "Fouls", "format": "integer", "winner": "lower", "all_time_winner": "neutral"},
            {"key": "cards_per_appearance", "label": "Cards Per Appearance", "format": "decimal3", "winner": "lower"},
        ],
    },
]

PLAYER_RANK_GROUPS = [
    {
        "title": "Rank Context",
        "metrics": [
            {"key": "appearance_rank", "label": "Appearance Rank", "format": "rank", "winner": "lower"},
            {"key": "goal_contribution_rank", "label": "Goal Contribution Rank", "format": "rank", "winner": "lower"},
            {"key": "goal_contribution_rate_rank", "label": "Goal Contribution Rate Rank", "format": "rank", "winner": "lower"},
            {"key": "position_appearance_rank", "label": "Position Appearance Rank", "format": "rank", "winner": "lower"},
            {"key": "position_role_rank", "label": "Position Role Rank", "format": "rank", "winner": "lower"},
        ],
    },
]

PLAYER_ROLE_GROUPS = {
    "forward": {
        "title": "Forward Metrics",
        "metrics": [
            {"key": "goals", "label": "Goals", "format": "integer", "winner": "higher"},
            {"key": "shots", "label": "Shots", "format": "integer", "winner": "higher"},
            {"key": "shots_per_appearance", "label": "Shots Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "shots_on_target", "label": "Shots On Target", "format": "integer", "winner": "higher"},
            {"key": "shots_on_target_per_appearance", "label": "SOT Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "shooting_accuracy_pct", "label": "Shooting Accuracy", "format": "percent", "winner": "higher"},
            {"key": "goal_conversion_pct", "label": "Goal Conversion", "format": "percent", "winner": "higher"},
            {"key": "big_chances_missed", "label": "Big Chances Missed", "format": "integer", "winner": "lower"},
        ],
    },
    "midfielder": {
        "title": "Midfielder Metrics",
        "metrics": [
            {"key": "assists", "label": "Assists", "format": "integer", "winner": "higher"},
            {"key": "passes", "label": "Passes", "format": "integer", "winner": "higher"},
            {"key": "passes_per_appearance", "label": "Passes Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "big_chances_created", "label": "Big Chances Created", "format": "integer", "winner": "higher"},
            {"key": "big_chances_created_per_appearance", "label": "Big Chances Created Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "crosses", "label": "Crosses", "format": "integer", "winner": "higher"},
            {"key": "cross_accuracy_pct", "label": "Cross Accuracy", "format": "percent", "winner": "higher"},
            {"key": "through_balls", "label": "Through Balls", "format": "integer", "winner": "higher"},
        ],
    },
    "defender": {
        "title": "Defender Metrics",
        "metrics": [
            {"key": "tackles", "label": "Tackles", "format": "integer", "winner": "higher"},
            {"key": "tackles_per_appearance", "label": "Tackles Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "tackle_success_pct", "label": "Tackle Success", "format": "percent", "winner": "higher"},
            {"key": "interceptions", "label": "Interceptions", "format": "integer", "winner": "higher"},
            {"key": "clearances", "label": "Clearances", "format": "integer", "winner": "higher"},
            {"key": "blocked_shots", "label": "Blocked Shots", "format": "integer", "winner": "higher"},
            {"key": "clean_sheets", "label": "Clean Sheets", "format": "integer", "winner": "higher"},
            {"key": "clean_sheets_per_appearance", "label": "Clean Sheets Per Appearance", "format": "decimal3", "winner": "higher"},
        ],
    },
    "goalkeeper": {
        "title": "Goalkeeper Metrics",
        "metrics": [
            {"key": "saves", "label": "Saves", "format": "integer", "winner": "higher"},
            {"key": "saves_per_appearance", "label": "Saves Per Appearance", "format": "decimal3", "winner": "higher"},
            {"key": "clean_sheets", "label": "Clean Sheets", "format": "integer", "winner": "higher"},
            {"key": "goals_conceded", "label": "Goals Conceded", "format": "integer", "winner": "lower"},
            {"key": "goals_conceded_per_appearance", "label": "Goals Conceded Per Appearance", "format": "decimal3", "winner": "lower"},
            {"key": "penalties_saved", "label": "Penalties Saved", "format": "integer", "winner": "higher"},
            {"key": "punches", "label": "Punches", "format": "integer", "winner": "higher"},
            {"key": "catches", "label": "Catches", "format": "integer", "winner": "higher"},
            {"key": "high_claims", "label": "High Claims", "format": "integer", "winner": "higher"},
        ],
    },
}


def format_player_metric(value, format_type):
    if value is None:
        return "N/A"

    if format_type == "percent":
        return f"{float(value):.2f}%"

    if format_type == "decimal3":
        return f"{float(value):.3f}"

    if format_type == "decimal":
        return f"{float(value):.2f}"

    if format_type == "rank":
        rank_value = float(value)
        if rank_value.is_integer():
            return f"#{int(rank_value)}"
        return f"#{rank_value:.2f}"

    return f"{int(value)}"


def player_metric_winner(metric, player_a, player_b, neutralize_raw_totals, comparable=True):
    if not comparable:
        return None

    winner_rule = metric.get("all_time_winner", metric["winner"]) if neutralize_raw_totals else metric["winner"]

    if winner_rule == "neutral":
        return None

    a_value = player_a.get(metric["key"])
    b_value = player_b.get(metric["key"])

    if a_value is None or b_value is None or a_value == b_value:
        return None

    if winner_rule == "lower":
        return "a" if a_value < b_value else "b"

    return "a" if a_value > b_value else "b"


def build_player_metric_sections(groups, player_a, player_b, neutralize_raw_totals=False, comparable=True):
    sections = []

    for group in groups:
        rows = []

        for metric in group["metrics"]:
            rows.append({
                "label": metric["label"],
                "description": metric.get("description") or PLAYER_COMPARISON_METRIC_DESCRIPTIONS.get(metric["key"]),
                "a_value": format_player_metric(player_a.get(metric["key"]), metric["format"]),
                "b_value": format_player_metric(player_b.get(metric["key"]), metric["format"]),
                "winner": player_metric_winner(metric, player_a, player_b, neutralize_raw_totals, comparable),
            })

        sections.append({
            "title": group["title"],
            "rows": rows,
        })

    return sections


def parse_club_badges(club_names):
    if not club_names:
        return []

    clubs = []
    seen = set()

    for club in club_names.split(","):
        clean_club = club.strip()
        if clean_club and clean_club not in seen and clean_club != "Unknown Team":
            seen.add(clean_club)
            clubs.append(clean_club)

    return clubs or ["Unknown Team"]


def prepare_player_summary(player, image_fallback_url):
    if not player:
        return None

    player["image_url"] = player.get("image_url") or image_fallback_url
    player["position_key"] = position_bucket(player.get("position_name"))
    player["club_badges"] = parse_club_badges(player.get("club_names"))
    player["clubs_represented"] = len([
        club for club in player["club_badges"]
        if club != "Unknown Team"
    ])
    return player


def player_metric_sentence(player_a, player_b, key, label, higher_is_better=True, suffix="", decimals=3, threshold=0):
    a_value = number_or_none(player_a.get(key))
    b_value = number_or_none(player_b.get(key))

    if a_value is None or b_value is None or abs(a_value - b_value) <= threshold:
        return None

    a_is_better = a_value > b_value if higher_is_better else a_value < b_value
    stronger = player_a if a_is_better else player_b
    weaker = player_b if a_is_better else player_a
    stronger_value = a_value if a_is_better else b_value
    weaker_value = b_value if a_is_better else a_value

    return (
        f"{stronger['player_name']} leads on {label}, "
        f"{stronger_value:.{decimals}f}{suffix} compared with "
        f"{weaker_value:.{decimals}f}{suffix} for {weaker['player_name']}."
    )


def player_rank_sentence(player_a, player_b, key, label):
    a_value = number_or_none(player_a.get(key))
    b_value = number_or_none(player_b.get(key))

    if a_value is None or b_value is None or a_value == b_value:
        return None

    stronger = player_a if a_value < b_value else player_b
    weaker = player_b if a_value < b_value else player_a
    stronger_value = a_value if a_value < b_value else b_value
    weaker_value = b_value if a_value < b_value else a_value

    return (
        f"{stronger['player_name']} has the better {label}, "
        f"{format_rank_summary(stronger_value)} versus {format_rank_summary(weaker_value)} "
        f"for {weaker['player_name']}."
    )


def build_player_comparison_insights(player_a, player_b, is_all_time, comparison_basis, positions_differ):
    insights = []

    if positions_differ:
        insights.append(
            f"{player_a['player_name']} is listed as a {player_a['position_name']}, "
            f"while {player_b['player_name']} is listed as a {player_b['position_name']}; "
            "universal metrics are more directly comparable than role-specific metrics."
        )

    if is_all_time and comparison_basis == "available" and player_a["seasons_played"] != player_b["seasons_played"]:
        insights.append(
            f"{player_a['player_name']} has {player_a['seasons_played']} season(s) in scope, "
            f"while {player_b['player_name']} has {player_b['seasons_played']}; per-appearance rates are safer than raw totals."
        )
    elif is_all_time and comparison_basis == "common":
        insights.append(
            f"This view compares only the {player_a['seasons_played']} shared season(s), "
            "so raw totals and rates use aligned coverage."
        )

    for sentence in [
        player_metric_sentence(player_a, player_b, "goal_contributions_per_appearance", "goal contributions per appearance"),
        player_metric_sentence(player_a, player_b, "goals_per_appearance", "goals per appearance"),
        player_metric_sentence(player_a, player_b, "assists_per_appearance", "assists per appearance"),
        player_rank_sentence(player_a, player_b, "position_role_rank", "position role rank"),
        player_metric_sentence(player_a, player_b, "cards_per_appearance", "cards per appearance", higher_is_better=False),
    ]:
        if sentence:
            insights.append(sentence)

    return insights[:6]


def build_player_role_sections(player_a, player_b, neutralize_raw_totals, positions_differ):
    player_a_role = PLAYER_ROLE_GROUPS.get(player_a["position_key"], PLAYER_ROLE_GROUPS["forward"])
    player_b_role = PLAYER_ROLE_GROUPS.get(player_b["position_key"], PLAYER_ROLE_GROUPS["forward"])

    if not positions_differ:
        return [{
            "title": player_a_role["title"],
            "comparison": True,
            "sections": build_player_metric_sections(
                [player_a_role],
                player_a,
                player_b,
                neutralize_raw_totals,
                comparable=True
            ),
        }]

    role_sections = []

    for player, role in [(player_a, player_a_role), (player_b, player_b_role)]:
        rows = []
        for metric in role["metrics"]:
            rows.append({
                "label": metric["label"],
                "description": metric.get("description") or PLAYER_COMPARISON_METRIC_DESCRIPTIONS.get(metric["key"]),
                "value": format_player_metric(player.get(metric["key"]), metric["format"]),
            })

        role_sections.append({
            "title": f"{player['player_name']} {role['title']}",
            "comparison": False,
            "player": player,
            "rows": rows,
        })

    return role_sections


def build_player_trend_data(rows, player_a, player_b):
    season_axis = []
    seen_seasons = set()

    for row in rows:
        if row["season_id"] not in seen_seasons:
            seen_seasons.add(row["season_id"])
            season_axis.append({
                "season_id": row["season_id"],
                "season_name": row["season_name"],
            })

    rows_by_player_and_season = {
        (row["player_id"], row["season_id"]): row
        for row in rows
    }

    metrics = [
        {"key": "appearances", "label": "Appearances"},
        {"key": "goal_contributions_per_appearance", "label": "Goal Contributions Per Appearance"},
        {"key": "goals_per_appearance", "label": "Goals Per Appearance"},
        {"key": "assists_per_appearance", "label": "Assists Per Appearance"},
        {"key": "cards_per_appearance", "label": "Cards Per Appearance"},
    ]

    for player in (player_a, player_b):
        if player["position_key"] == "goalkeeper":
            metrics.append({"key": "saves_per_appearance", "label": "Saves Per Appearance"})
        elif player["position_key"] == "defender":
            metrics.append({"key": "tackles_per_appearance", "label": "Tackles Per Appearance"})
        elif player["position_key"] == "midfielder":
            metrics.append({"key": "passes_per_appearance", "label": "Passes Per Appearance"})
        elif player["position_key"] == "forward":
            metrics.append({"key": "shots_on_target_per_appearance", "label": "SOT Per Appearance"})

    unique_metrics = []
    seen_metric_keys = set()
    for metric in metrics:
        if metric["key"] not in seen_metric_keys:
            seen_metric_keys.add(metric["key"])
            unique_metrics.append(metric)

    charts = []
    for metric in unique_metrics:
        charts.append({
            "key": metric["key"],
            "label": metric["label"],
            "labels": [season["season_name"] for season in season_axis],
            "player_a_name": player_a["player_name"],
            "player_b_name": player_b["player_name"],
            "player_a_values": [
                chart_number(rows_by_player_and_season.get((player_a["player_id"], season["season_id"]), {}).get(metric["key"]))
                for season in season_axis
            ],
            "player_b_values": [
                chart_number(rows_by_player_and_season.get((player_b["player_id"], season["season_id"]), {}).get(metric["key"]))
                for season in season_axis
            ],
        })

    return charts

def player_comparison():
    selected_season = request.args.get("season") or "all"
    comparison_basis = request.args.get("basis") or "available"
    selected_position = request.args.get("position") or ""
    player_a_id = request.args.get("player_a", type=int)
    player_b_id = request.args.get("player_b", type=int)

    if comparison_basis not in ("available", "common"):
        comparison_basis = "available"

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    cur.execute("SELECT position_name FROM position ORDER BY position_name;")
    positions = cur.fetchall()

    player_filter_clauses = ["EXISTS (SELECT 1 FROM player_season_stats pss WHERE pss.player_id = p.player_id)"]
    player_filter_params = []

    if selected_position:
        player_filter_clauses.append("lp.position_name = %s")
        player_filter_params.append(selected_position)

    player_filter_sql = " AND ".join(player_filter_clauses)
    selected_a_for_filter = player_a_id or 0
    selected_b_for_filter = player_b_id or 0

    cur.execute(f"""
        WITH latest_position AS (
            SELECT
                pss.player_id,
                pos.position_name,
                ROW_NUMBER() OVER (
                    PARTITION BY pss.player_id
                    ORDER BY pss.season_id DESC
                ) AS position_rank
            FROM player_season_stats pss
            INNER JOIN position pos
                ON pss.position_id = pos.position_id
        ),
        player_clubs AS (
            SELECT
                pts.player_id,
                STRING_AGG(DISTINCT t.team_name, ', ' ORDER BY t.team_name) AS club_names
            FROM player_team_season pts
            INNER JOIN team t
                ON pts.team_id = t.team_id
            GROUP BY pts.player_id
        )
        SELECT
            p.player_id,
            p.player_name,
            lp.position_name,
            COALESCE(pc.club_names, 'Unknown Team') AS club_names
        FROM player p
        INNER JOIN latest_position lp
            ON p.player_id = lp.player_id
           AND lp.position_rank = 1
        LEFT JOIN player_clubs pc
            ON p.player_id = pc.player_id
        WHERE ({player_filter_sql})
           OR p.player_id IN (%s, %s)
        ORDER BY p.player_name;
    """, player_filter_params + [selected_a_for_filter, selected_b_for_filter])
    player_options = cur.fetchall()
    player_selector_options = []
    for player in player_options:
        club_names = player["club_names"] or "Unknown Team"
        player_selector_options.append({
            "player_id": player["player_id"],
            "display_label": f"{player['player_name']} - {player['position_name']} - {club_names}",
        })
    selected_player_a_label = next(
        (
            player["display_label"]
            for player in player_selector_options
            if player["player_id"] == player_a_id
        ),
        "",
    )
    selected_player_b_label = next(
        (
            player["display_label"]
            for player in player_selector_options
            if player["player_id"] == player_b_id
        ),
        "",
    )

    error_message = None
    season_count_warning = None
    position_warning = None
    rank_warning = None
    summary_insights = []
    universal_sections = []
    rank_sections = []
    role_sections = []
    trend_charts = []
    season_rows = []
    player_a = None
    player_b = None
    is_all_time = selected_season == "all"
    positions_differ = False

    if player_a_id and player_b_id:
        if player_a_id == player_b_id:
            error_message = "Please choose two different players to compare."
        else:
            if is_all_time and comparison_basis == "common":
                scope_condition = "v.season_id IN (SELECT season_id FROM common_seasons)"
                scope_params = []
            elif is_all_time:
                scope_condition = "TRUE"
                scope_params = []
            else:
                scope_condition = "v.season_name = %s"
                scope_params = [selected_season]

            rank_min_appearances = 10 if is_all_time else 5

            cur.execute(f"""
                WITH selected_players AS (
                    SELECT
                        %s::integer AS player_a_id,
                        %s::integer AS player_b_id
                ),
                common_seasons AS (
                    SELECT
                        v.season_id
                    FROM v_player_season_summary v
                    CROSS JOIN selected_players sp
                    WHERE v.player_id IN (sp.player_a_id, sp.player_b_id)
                    GROUP BY v.season_id
                    HAVING COUNT(DISTINCT v.player_id) = 2
                ),
                scoped_all_players AS (
                    SELECT v.*
                    FROM v_player_season_summary v
                    WHERE {scope_condition}
                ),
                aggregate_base AS (
                    SELECT
                        player_id,
                        MAX(player_name) AS player_name,
                        MAX(normalized_player_name) AS normalized_player_name,
                        (ARRAY_AGG(image_url ORDER BY season_id DESC NULLS LAST))[1] AS image_url,
                        (ARRAY_AGG(position_id ORDER BY season_id DESC NULLS LAST))[1] AS position_id,
                        (ARRAY_AGG(position_name ORDER BY season_id DESC NULLS LAST))[1] AS position_name,
                        (ARRAY_AGG(position_group ORDER BY season_id DESC NULLS LAST))[1] AS position_group,
                        STRING_AGG(DISTINCT club_names, ', ' ORDER BY club_names) AS club_names,
                        COUNT(*)::integer AS seasons_played,
                        SUM(appearances)::integer AS appearances,
                        SUM(clean_sheets)::integer AS clean_sheets,
                        SUM(goals_conceded)::integer AS goals_conceded,
                        SUM(tackles)::integer AS tackles,
                        ROUND(
                            SUM(tackle_success_pct * tackles) FILTER (
                                WHERE tackle_success_pct IS NOT NULL AND tackles IS NOT NULL AND tackles > 0
                            ) / NULLIF(
                                SUM(tackles) FILTER (
                                    WHERE tackle_success_pct IS NOT NULL AND tackles IS NOT NULL AND tackles > 0
                                ),
                                0
                            ),
                            2
                        ) AS tackle_success_pct,
                        SUM(blocked_shots)::integer AS blocked_shots,
                        SUM(interceptions)::integer AS interceptions,
                        SUM(clearances)::integer AS clearances,
                        SUM(recoveries)::integer AS recoveries,
                        SUM(assists)::integer AS assists,
                        SUM(passes)::integer AS passes,
                        SUM(big_chances_created)::integer AS big_chances_created,
                        SUM(crosses)::integer AS crosses,
                        ROUND(
                            SUM(cross_accuracy_pct * crosses) FILTER (
                                WHERE cross_accuracy_pct IS NOT NULL AND crosses IS NOT NULL AND crosses > 0
                            ) / NULLIF(
                                SUM(crosses) FILTER (
                                    WHERE cross_accuracy_pct IS NOT NULL AND crosses IS NOT NULL AND crosses > 0
                                ),
                                0
                            ),
                            2
                        ) AS cross_accuracy_pct,
                        SUM(through_balls)::integer AS through_balls,
                        SUM(accurate_long_balls)::integer AS accurate_long_balls,
                        SUM(yellow_cards)::integer AS yellow_cards,
                        SUM(red_cards)::integer AS red_cards,
                        SUM(fouls)::integer AS fouls,
                        SUM(offsides)::integer AS offsides,
                        SUM(goals)::integer AS goals,
                        SUM(hit_woodwork)::integer AS hit_woodwork,
                        SUM(penalties_scored)::integer AS penalties_scored,
                        SUM(freekicks_scored)::integer AS freekicks_scored,
                        SUM(shots)::integer AS shots,
                        SUM(shots_on_target)::integer AS shots_on_target,
                        ROUND(
                            SUM(shooting_accuracy_pct * shots) FILTER (
                                WHERE shooting_accuracy_pct IS NOT NULL AND shots IS NOT NULL AND shots > 0
                            ) / NULLIF(
                                SUM(shots) FILTER (
                                    WHERE shooting_accuracy_pct IS NOT NULL AND shots IS NOT NULL AND shots > 0
                                ),
                                0
                            ),
                            2
                        ) AS shooting_accuracy_pct,
                        SUM(big_chances_missed)::integer AS big_chances_missed,
                        SUM(saves)::integer AS saves,
                        SUM(penalties_saved)::integer AS penalties_saved,
                        SUM(punches)::integer AS punches,
                        SUM(high_claims)::integer AS high_claims,
                        SUM(catches)::integer AS catches,
                        SUM(sweeper_clearances)::integer AS sweeper_clearances,
                        SUM(goal_contributions)::integer AS goal_contributions
                    FROM scoped_all_players
                    GROUP BY player_id
                ),
                metrics AS (
                    SELECT
                        *,
                        CASE
                            WHEN yellow_cards IS NULL AND red_cards IS NULL THEN NULL
                            ELSE COALESCE(yellow_cards, 0) + COALESCE(red_cards, 0)
                        END AS cards,
                        ROUND(goals::numeric / NULLIF(appearances, 0), 3) AS goals_per_appearance,
                        ROUND(assists::numeric / NULLIF(appearances, 0), 3) AS assists_per_appearance,
                        ROUND(goal_contributions::numeric / NULLIF(appearances, 0), 3) AS goal_contributions_per_appearance,
                        ROUND((COALESCE(yellow_cards, 0) + COALESCE(red_cards, 0))::numeric / NULLIF(appearances, 0), 3) AS cards_per_appearance,
                        ROUND(fouls::numeric / NULLIF(appearances, 0), 3) AS fouls_per_appearance,
                        ROUND(shots::numeric / NULLIF(appearances, 0), 3) AS shots_per_appearance,
                        ROUND(shots_on_target::numeric / NULLIF(appearances, 0), 3) AS shots_on_target_per_appearance,
                        ROUND(goals::numeric / NULLIF(shots, 0) * 100, 2) AS goal_conversion_pct,
                        ROUND(passes::numeric / NULLIF(appearances, 0), 3) AS passes_per_appearance,
                        ROUND(big_chances_created::numeric / NULLIF(appearances, 0), 3) AS big_chances_created_per_appearance,
                        ROUND(crosses::numeric / NULLIF(appearances, 0), 3) AS crosses_per_appearance,
                        ROUND(tackles::numeric / NULLIF(appearances, 0), 3) AS tackles_per_appearance,
                        ROUND(interceptions::numeric / NULLIF(appearances, 0), 3) AS interceptions_per_appearance,
                        ROUND(clearances::numeric / NULLIF(appearances, 0), 3) AS clearances_per_appearance,
                        ROUND(blocked_shots::numeric / NULLIF(appearances, 0), 3) AS blocked_shots_per_appearance,
                        ROUND(clean_sheets::numeric / NULLIF(appearances, 0), 3) AS clean_sheets_per_appearance,
                        ROUND(saves::numeric / NULLIF(appearances, 0), 3) AS saves_per_appearance,
                        ROUND(goals_conceded::numeric / NULLIF(appearances, 0), 3) AS goals_conceded_per_appearance
                    FROM aggregate_base
                ),
                scored AS (
                    SELECT
                        *,
                        CASE
                            WHEN position_name = 'Forward' THEN
                                COALESCE(goals_per_appearance, 0) * 4
                                + COALESCE(goal_contributions_per_appearance, 0) * 2
                                + COALESCE(shots_on_target_per_appearance, 0)
                            WHEN position_name = 'Midfielder' THEN
                                COALESCE(assists_per_appearance, 0) * 4
                                + COALESCE(big_chances_created_per_appearance, 0) * 2
                                + COALESCE(passes_per_appearance, 0) / 100
                            WHEN position_name = 'Defender' THEN
                                COALESCE(clean_sheets_per_appearance, 0) * 3
                                + COALESCE(tackles_per_appearance, 0)
                                + COALESCE(interceptions_per_appearance, 0)
                                + COALESCE(clearances_per_appearance, 0) / 5
                            WHEN position_name = 'Goalkeeper' THEN
                                COALESCE(clean_sheets_per_appearance, 0) * 4
                                + COALESCE(saves_per_appearance, 0)
                                - COALESCE(goals_conceded_per_appearance, 0)
                            ELSE NULL
                        END AS position_role_score
                    FROM metrics
                ),
                eligible AS (
                    SELECT *
                    FROM scored
                    WHERE appearances >= %s
                ),
                ranked AS (
                    SELECT
                        player_id,
                        RANK() OVER (
                            ORDER BY appearances DESC, player_name ASC
                        )::integer AS appearance_rank,
                        RANK() OVER (
                            ORDER BY goal_contributions DESC NULLS LAST, goals DESC NULLS LAST, assists DESC NULLS LAST, player_name ASC
                        )::integer AS goal_contribution_rank,
                        RANK() OVER (
                            ORDER BY goal_contributions_per_appearance DESC NULLS LAST, goal_contributions DESC NULLS LAST, player_name ASC
                        )::integer AS goal_contribution_rate_rank,
                        RANK() OVER (
                            PARTITION BY position_id
                            ORDER BY appearances DESC, player_name ASC
                        )::integer AS position_appearance_rank,
                        RANK() OVER (
                            PARTITION BY position_id
                            ORDER BY position_role_score DESC NULLS LAST, appearances DESC, player_name ASC
                        )::integer AS position_role_rank
                    FROM eligible
                )
                SELECT
                    scored.*,
                    ranked.appearance_rank,
                    ranked.goal_contribution_rank,
                    ranked.goal_contribution_rate_rank,
                    ranked.position_appearance_rank,
                    ranked.position_role_rank
                FROM scored
                LEFT JOIN ranked
                    ON scored.player_id = ranked.player_id
                CROSS JOIN selected_players sp
                WHERE scored.player_id IN (sp.player_a_id, sp.player_b_id)
                ORDER BY CASE
                    WHEN scored.player_id = sp.player_a_id THEN 1
                    WHEN scored.player_id = sp.player_b_id THEN 2
                    ELSE 3
                END;
            """, [player_a_id, player_b_id] + scope_params + [rank_min_appearances])
            summary_rows = cur.fetchall()

            summaries_by_player = {row["player_id"]: row for row in summary_rows}
            player_a = prepare_player_summary(
                summaries_by_player.get(player_a_id),
                url_for("static", filename="images/player-placeholder.png")
            )
            player_b = prepare_player_summary(
                summaries_by_player.get(player_b_id),
                url_for("static", filename="images/player-placeholder.png")
            )

            if not player_a or not player_b:
                if comparison_basis == "common" and is_all_time:
                    error_message = "These players do not share any seasons in this dataset."
                else:
                    error_message = "One or both players do not have data for the selected scope."
            else:
                cur.execute(f"""
                    WITH selected_players AS (
                        SELECT
                            %s::integer AS player_a_id,
                            %s::integer AS player_b_id
                    ),
                    common_seasons AS (
                        SELECT
                            v.season_id
                        FROM v_player_season_summary v
                        CROSS JOIN selected_players sp
                        WHERE v.player_id IN (sp.player_a_id, sp.player_b_id)
                        GROUP BY v.season_id
                        HAVING COUNT(DISTINCT v.player_id) = 2
                    )
                    SELECT v.*
                    FROM v_player_season_rankings v
                    CROSS JOIN selected_players sp
                    WHERE v.player_id IN (sp.player_a_id, sp.player_b_id)
                      AND {scope_condition}
                    ORDER BY v.season_id, v.player_id;
                """, [player_a_id, player_b_id] + scope_params)
                season_rows = cur.fetchall()

                positions_differ = player_a["position_key"] != player_b["position_key"]
                neutralize_raw_totals = is_all_time and comparison_basis == "available"
                universal_sections = build_player_metric_sections(
                    PLAYER_UNIVERSAL_GROUPS,
                    player_a,
                    player_b,
                    neutralize_raw_totals,
                    comparable=True
                )
                rank_sections = build_player_metric_sections(
                    PLAYER_RANK_GROUPS,
                    player_a,
                    player_b,
                    neutralize_raw_totals=False,
                    comparable=True
                )
                role_sections = build_player_role_sections(
                    player_a,
                    player_b,
                    neutralize_raw_totals,
                    positions_differ
                )
                trend_charts = build_player_trend_data(season_rows, player_a, player_b)
                summary_insights = build_player_comparison_insights(
                    player_a,
                    player_b,
                    is_all_time,
                    comparison_basis,
                    positions_differ
                )

                if positions_differ:
                    position_warning = (
                        f"{player_a['player_name']} and {player_b['player_name']} have different primary positions. "
                        "Universal metrics are directly comparable; role-specific panels are shown separately."
                    )

                if is_all_time and comparison_basis == "available" and player_a["seasons_played"] != player_b["seasons_played"]:
                    season_count_warning = (
                        f"{player_a['player_name']} has {player_a['seasons_played']} season(s) in scope, "
                        f"while {player_b['player_name']} has {player_b['seasons_played']}. "
                        "Per-appearance rates and Common Seasons Only are safer for direct comparison."
                    )

                if player_a.get("appearance_rank") is None or player_b.get("appearance_rank") is None:
                    rank_warning = (
                        f"Some rank metrics are N/A because scoped rank eligibility requires at least "
                        f"{rank_min_appearances} appearances."
                    )

    cur.close()

    return render_template(
        "player_comparison.html",
        title="Player Comparison",
        seasons=seasons,
        positions=positions,
        player_options=player_options,
        player_selector_options=player_selector_options,
        selected_season=selected_season,
        comparison_basis=comparison_basis,
        selected_position=selected_position,
        selected_player_a_label=selected_player_a_label,
        selected_player_b_label=selected_player_b_label,
        selected_player_a=player_a_id,
        selected_player_b=player_b_id,
        is_all_time=is_all_time,
        error_message=error_message,
        season_count_warning=season_count_warning,
        position_warning=position_warning,
        rank_warning=rank_warning,
        summary_insights=summary_insights,
        player_a=player_a,
        player_b=player_b,
        positions_differ=positions_differ,
        universal_sections=universal_sections,
        rank_sections=rank_sections,
        role_sections=role_sections,
        trend_charts=trend_charts
    )

