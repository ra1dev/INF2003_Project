from flask import render_template, request
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


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


