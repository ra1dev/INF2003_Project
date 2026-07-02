from flask import render_template, request
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


# These sections define the metric groups and labels shown on the team comparison page.
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
    """Assemble the comparison rows used by the team comparison template."""
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
    """Build trend-chart data for the selected seasons and teams."""
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


def team_comparison():
    selected_season = request.args.get("season") or "all"
    comparison_basis = request.args.get("basis") or "available"
    team_a_id = request.args.get("team_a", type=int)
    team_b_id = request.args.get("team_b", type=int)

    if comparison_basis not in ("available", "common"):
        comparison_basis = "available"

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    cur.execute("""
        SELECT
            team_id,
            team_name,
            COALESCE(
                team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(team_name, ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo
        FROM team
        ORDER BY team_name;
    """)
    teams = cur.fetchall()
    team_selector_options = [
        {
            "team_id": team["team_id"],
            "display_label": team["team_name"],
        }
        for team in teams
    ]
    selected_team_a_label = next(
        (
            team["display_label"]
            for team in team_selector_options
            if team["team_id"] == team_a_id
        ),
        ""
    )
    selected_team_b_label = next(
        (
            team["display_label"]
            for team in team_selector_options
            if team["team_id"] == team_b_id
        ),
        ""
    )

    error_message = None
    comparison_sections = []
    head_to_head = None
    team_a = None
    team_b = None
    season_rows = []
    team_a_highlights = []
    team_b_highlights = []
    trend_charts = []
    summary_insights = []
    season_count_warning = None
    is_all_time = selected_season == "all"

    if team_a_id and team_b_id:
        if team_a_id == team_b_id:
            error_message = "Please choose two different teams to compare."
        else:
            if is_all_time:
                scope_condition = """
                   AND (
                        %s <> 'common'
                        OR r.season_id IN (SELECT season_id FROM common_seasons)
                   )
                """
                scope_params = [team_a_id, team_b_id, comparison_basis]
            else:
                scope_condition = "AND r.season_name = %s"
                scope_params = [team_a_id, team_b_id, selected_season]

            cur.execute("""
                WITH selected_teams AS (
                    SELECT
                        %s::integer AS team_a_id,
                        %s::integer AS team_b_id
                ),
                common_seasons AS (
                    SELECT
                        r.season_id
                    FROM v_team_season_rankings r
                    CROSS JOIN selected_teams st
                    WHERE r.team_id IN (st.team_a_id, st.team_b_id)
                    GROUP BY r.season_id
                    HAVING COUNT(DISTINCT r.team_id) = 2
                ),
                scoped AS (
                    SELECT r.*
                    FROM v_team_season_rankings r
                    CROSS JOIN selected_teams st
                    WHERE r.team_id IN (st.team_a_id, st.team_b_id)
                    {scope_condition}
                ),
                team_aggregate AS (
                    SELECT
                        team_id,
                        team_name,
                        team_logo,
                        COUNT(*)::integer AS seasons_played,
                        SUM(matches_played)::integer AS matches_played,
                        SUM(wins)::integer AS wins,
                        SUM(draws)::integer AS draws,
                        SUM(losses)::integer AS losses,
                        SUM(points)::integer AS points,
                        SUM(goals_for)::integer AS goals_for,
                        SUM(goals_against)::integer AS goals_against,
                        SUM(goal_difference)::integer AS goal_difference,
                        SUM(shots)::integer AS shots,
                        SUM(shots_allowed)::integer AS shots_allowed,
                        SUM(shot_difference)::integer AS shot_difference,
                        SUM(shots_on_target)::integer AS shots_on_target,
                        SUM(shots_on_target_allowed)::integer AS shots_on_target_allowed,
                        SUM(shots_on_target_difference)::integer AS shots_on_target_difference,
                        SUM(corners)::integer AS corners,
                        SUM(corners_allowed)::integer AS corners_allowed,
                        SUM(corner_difference)::integer AS corner_difference,
                        SUM(fouls)::integer AS fouls,
                        SUM(yellow_cards)::integer AS yellow_cards,
                        SUM(red_cards)::integer AS red_cards,
                        SUM(clean_sheets)::integer AS clean_sheets,
                        SUM(failed_to_score)::integer AS failed_to_score,
                        SUM(home_matches)::integer AS home_matches,
                        SUM(home_wins)::integer AS home_wins,
                        SUM(home_points)::integer AS home_points,
                        SUM(away_matches)::integer AS away_matches,
                        SUM(away_wins)::integer AS away_wins,
                        SUM(away_points)::integer AS away_points,
                        ROUND(AVG(league_position), 2) AS average_league_position,
                        MIN(league_position)::integer AS best_league_position,
                        MAX(league_position)::integer AS worst_league_position,
                        ROUND(AVG(attack_rank), 2) AS average_attack_rank,
                        ROUND(AVG(defense_rank), 2) AS average_defense_rank,
                        ROUND(AVG(pressure_rank), 2) AS average_pressure_rank,
                        ROUND(AVG(home_rank), 2) AS average_home_rank,
                        ROUND(AVG(away_rank), 2) AS average_away_rank,
                        ROUND(AVG(discipline_rank), 2) AS average_discipline_rank
                    FROM scoped
                    GROUP BY team_id, team_name, team_logo
                )
                SELECT
                    *,
                    ROUND(points::numeric / NULLIF(matches_played, 0), 2) AS points_per_match,
                    ROUND(wins::numeric / NULLIF(matches_played, 0) * 100, 2) AS win_rate_pct,
                    ROUND(goals_for::numeric / NULLIF(matches_played, 0), 2) AS goals_per_match,
                    ROUND(goals_against::numeric / NULLIF(matches_played, 0), 2) AS goals_conceded_per_match,
                    ROUND(goal_difference::numeric / NULLIF(matches_played, 0), 2) AS goal_difference_per_match,
                    ROUND(shots::numeric / NULLIF(matches_played, 0), 2) AS shots_per_match,
                    ROUND(shots_allowed::numeric / NULLIF(matches_played, 0), 2) AS shots_allowed_per_match,
                    ROUND(shot_difference::numeric / NULLIF(matches_played, 0), 2) AS shot_difference_per_match,
                    ROUND(shots_on_target::numeric / NULLIF(matches_played, 0), 2) AS shots_on_target_per_match,
                    ROUND(shots_on_target_allowed::numeric / NULLIF(matches_played, 0), 2) AS shots_on_target_allowed_per_match,
                    ROUND(shots_on_target_difference::numeric / NULLIF(matches_played, 0), 2) AS shots_on_target_difference_per_match,
                    ROUND(shots_on_target::numeric / NULLIF(shots, 0) * 100, 2) AS shot_accuracy_pct,
                    ROUND(goals_for::numeric / NULLIF(shots, 0) * 100, 2) AS goal_conversion_pct,
                    ROUND(shots::numeric / NULLIF(shots + shots_allowed, 0) * 100, 2) AS shot_share_pct,
                    ROUND(shots_on_target::numeric / NULLIF(shots_on_target + shots_on_target_allowed, 0) * 100, 2) AS shot_on_target_share_pct,
                    ROUND(goals_for::numeric / NULLIF(goals_for + goals_against, 0) * 100, 2) AS goal_share_pct,
                    ROUND(corners::numeric / NULLIF(matches_played, 0), 2) AS corners_per_match,
                    ROUND(corners_allowed::numeric / NULLIF(matches_played, 0), 2) AS corners_allowed_per_match,
                    ROUND(corner_difference::numeric / NULLIF(matches_played, 0), 2) AS corner_difference_per_match,
                    ROUND(corners::numeric / NULLIF(corners + corners_allowed, 0) * 100, 2) AS corner_share_pct,
                    ROUND(clean_sheets::numeric / NULLIF(matches_played, 0) * 100, 2) AS clean_sheet_rate_pct,
                    ROUND(failed_to_score::numeric / NULLIF(matches_played, 0) * 100, 2) AS failed_to_score_rate_pct,
                    ROUND(fouls::numeric / NULLIF(matches_played, 0), 2) AS fouls_per_match,
                    (yellow_cards + red_cards) AS cards,
                    ROUND((yellow_cards + red_cards)::numeric / NULLIF(matches_played, 0), 2) AS cards_per_match,
                    (yellow_cards + red_cards * 3) AS discipline_score,
                    ROUND((yellow_cards + red_cards * 3)::numeric / NULLIF(matches_played, 0), 2) AS discipline_score_per_match,
                    ROUND(home_points::numeric / NULLIF(home_matches, 0), 2) AS home_points_per_match,
                    ROUND(home_wins::numeric / NULLIF(home_matches, 0) * 100, 2) AS home_win_rate_pct,
                    ROUND(away_points::numeric / NULLIF(away_matches, 0), 2) AS away_points_per_match,
                    ROUND(away_wins::numeric / NULLIF(away_matches, 0) * 100, 2) AS away_win_rate_pct
                FROM team_aggregate
                ORDER BY CASE
                    WHEN team_id = (SELECT team_a_id FROM selected_teams) THEN 1
                    WHEN team_id = (SELECT team_b_id FROM selected_teams) THEN 2
                    ELSE 3
                END;
            """.format(scope_condition=scope_condition), scope_params)
            summary_rows = cur.fetchall()

            summaries_by_team = {row["team_id"]: row for row in summary_rows}
            team_a = summaries_by_team.get(team_a_id)
            team_b = summaries_by_team.get(team_b_id)

            if not team_a or not team_b:
                error_message = "One or both teams do not have match data for the selected scope."
            else:
                cur.execute("""
                    WITH selected_teams AS (
                        SELECT
                            %s::integer AS team_a_id,
                            %s::integer AS team_b_id
                    ),
                    common_seasons AS (
                        SELECT
                            r.season_id
                        FROM v_team_season_rankings r
                        CROSS JOIN selected_teams st
                        WHERE r.team_id IN (st.team_a_id, st.team_b_id)
                        GROUP BY r.season_id
                        HAVING COUNT(DISTINCT r.team_id) = 2
                    )
                    SELECT r.*
                    FROM v_team_season_rankings r
                    CROSS JOIN selected_teams st
                    WHERE r.team_id IN (st.team_a_id, st.team_b_id)
                    {scope_condition}
                    ORDER BY r.season_id, r.team_id;
                """.format(scope_condition=scope_condition), scope_params)
                season_rows = cur.fetchall()

                team_a_rows = [row for row in season_rows if row["team_id"] == team_a_id]
                team_b_rows = [row for row in season_rows if row["team_id"] == team_b_id]
                team_a_highlights = build_team_season_highlights(team_a_rows)
                team_b_highlights = build_team_season_highlights(team_b_rows)
                trend_charts = build_team_trend_data(season_rows, team_a, team_b)

                neutralize_raw_totals = is_all_time and comparison_basis == "available"
                comparison_sections = build_team_comparison_sections(team_a, team_b, neutralize_raw_totals)

                if is_all_time and comparison_basis == "available" and team_a["seasons_played"] != team_b["seasons_played"]:
                    season_count_warning = (
                        f"{team_a['team_name']} has {team_a['seasons_played']} seasons in this dataset, "
                        f"while {team_b['team_name']} has {team_b['seasons_played']}. "
                        "Rate metrics and the Common Seasons Only basis are safer for direct comparison."
                    )

                if not is_all_time:
                    head_to_head_condition = "AND s.season_name = %s"
                    head_to_head_params = [team_a_id, team_b_id, selected_season]
                elif comparison_basis == "common":
                    head_to_head_condition = "AND mr.season_id IN (SELECT season_id FROM common_seasons)"
                    head_to_head_params = [team_a_id, team_b_id]
                else:
                    head_to_head_condition = ""
                    head_to_head_params = [team_a_id, team_b_id]

                cur.execute(f"""
                    WITH selected_teams AS (
                        SELECT
                            %s::integer AS team_a_id,
                            %s::integer AS team_b_id
                    ),
                    common_seasons AS (
                        SELECT
                            r.season_id
                        FROM v_team_season_rankings r
                        CROSS JOIN selected_teams st
                        WHERE r.team_id IN (st.team_a_id, st.team_b_id)
                        GROUP BY r.season_id
                        HAVING COUNT(DISTINCT r.team_id) = 2
                    ),
                    head_to_head_matches AS (
                        SELECT
                            CASE
                                WHEN mr.home_team_id = st.team_a_id THEN mr.full_time_home_goals
                                ELSE mr.full_time_away_goals
                            END AS team_a_goals,
                            CASE
                                WHEN mr.home_team_id = st.team_a_id THEN mr.full_time_away_goals
                                ELSE mr.full_time_home_goals
                            END AS team_b_goals
                        FROM match_record mr
                        INNER JOIN season s
                            ON mr.season_id = s.season_id
                        CROSS JOIN selected_teams st
                        WHERE (
                            (mr.home_team_id = st.team_a_id AND mr.away_team_id = st.team_b_id)
                            OR
                            (mr.home_team_id = st.team_b_id AND mr.away_team_id = st.team_a_id)
                        )
                        {head_to_head_condition}
                    )
                    SELECT
                        COUNT(*)::integer AS matches_played,
                        COALESCE(SUM(CASE WHEN team_a_goals > team_b_goals THEN 1 ELSE 0 END), 0)::integer AS team_a_wins,
                        COALESCE(SUM(CASE WHEN team_b_goals > team_a_goals THEN 1 ELSE 0 END), 0)::integer AS team_b_wins,
                        COALESCE(SUM(CASE WHEN team_a_goals = team_b_goals THEN 1 ELSE 0 END), 0)::integer AS draws,
                        COALESCE(SUM(team_a_goals), 0)::integer AS team_a_goals,
                        COALESCE(SUM(team_b_goals), 0)::integer AS team_b_goals
                    FROM head_to_head_matches;
                """, head_to_head_params)
                head_to_head = cur.fetchone()
                summary_insights = build_team_comparison_insights(
                    team_a,
                    team_b,
                    is_all_time,
                    comparison_basis,
                    head_to_head
                )

    cur.close()

    return render_template(
        "team_comparison.html",
        title="Team Comparison",
        seasons=seasons,
        teams=teams,
        team_selector_options=team_selector_options,
        selected_season=selected_season,
        comparison_basis=comparison_basis,
        selected_team_a=team_a_id,
        selected_team_b=team_b_id,
        selected_team_a_label=selected_team_a_label,
        selected_team_b_label=selected_team_b_label,
        is_all_time=is_all_time,
        error_message=error_message,
        season_count_warning=season_count_warning,
        team_a=team_a,
        team_b=team_b,
        comparison_sections=comparison_sections,
        head_to_head=head_to_head,
        team_a_highlights=team_a_highlights,
        team_b_highlights=team_b_highlights,
        trend_charts=trend_charts,
        summary_insights=summary_insights
    )

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


