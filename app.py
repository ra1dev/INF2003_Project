from flask import Flask, render_template, request, url_for
from psycopg2.extras import RealDictCursor
from Backend.db_conn import get_db, init_app

app = Flask(
    __name__,
    template_folder="Frontend/templates",
    static_folder="Frontend/static"
)

init_app(app)


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
            mr.match_date,
            home.team_name AS home_team,
            away.team_name AS away_team,
            mr.full_time_home_goals,
            mr.full_time_away_goals
        FROM match_record mr
        INNER JOIN team home 
            ON mr.home_team_id = home.team_id
        INNER JOIN team away 
            ON mr.away_team_id = away.team_id
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

    return render_template(
        "match_detail.html",
        title="Match Stats",
        stats=stats,
        match=match
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

@app.route("/season-recap")
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