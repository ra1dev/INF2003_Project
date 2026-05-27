from flask import Flask, render_template, request
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
            t.team_logo

        FROM player p

        LEFT JOIN playerseasonstats pss
            ON p.player_id = pss.player_id

        LEFT JOIN team t
            ON pss.team_id = t.team_id

        WHERE 1=1
    """

    params = []

    # Player Search
    if search:
        query += " AND p.player_name ILIKE %s"
        params.append(f"%{search}%")

    # Team Filter
    if team:
        query += " AND t.team_name = %s"
        params.append(team)

    query += """
        ORDER BY p.player_name;
    """

    cur.execute(query, params)

    players = cur.fetchall()

    # Get teams for dropdown
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
                p.player_name,
                p.player_image,
                s.season_name,
                t.team_name,
                pss.appearances,
                pss.goals,
                pss.assists,
                pss.yellow_cards,
                pss.red_cards
            FROM player p
            INNER JOIN playerseasonstats pss ON p.player_id = pss.player_id
            INNER JOIN season s ON pss.season_id = s.season_id
            INNER JOIN team t ON pss.team_id = t.team_id
            WHERE p.player_id = %s
            ORDER BY s.season_name;
        """, (player_id,))

    stats = cur.fetchall()
    cur.close()

    return render_template("player_detail.html", title="Player Stats", stats=stats)


@app.route("/teams")
def teams():
    search = request.args.get("search")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            team_id,
            team_name,
            team_logo
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

    return render_template("teams.html", title="Teams", teams=teams, search=search)


@app.route("/team/<int:team_id>")
def team_detail(team_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            t.team_name,
            t.team_logo,
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
        INNER JOIN matchteamstats mts
            ON t.team_id = mts.team_id
        INNER JOIN matchrecord mr
            ON mts.match_id = mr.match_id
        INNER JOIN season s
            ON mr.season_id = s.season_id
        WHERE t.team_id = %s
        GROUP BY t.team_name, t.team_logo, s.season_name
        ORDER BY s.season_name;
    """, (team_id,))

    stats = cur.fetchall()
    cur.close()

    return render_template("team_detail.html", title="Team Stats", stats=stats)


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
            home.team_logo AS home_logo,
            away.team_name AS away_team,
            away.team_logo AS away_logo,
            mr.full_time_home_goals,
            mr.full_time_away_goals,
            mr.full_time_result
        FROM matchrecord mr
        INNER JOIN season s ON mr.season_id = s.season_id
        INNER JOIN team home ON mr.home_team_id = home.team_id
        INNER JOIN team away ON mr.away_team_id = away.team_id
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

    # Match title info
    cur.execute("""
        SELECT
            mr.match_date,
            home.team_name AS home_team,
            away.team_name AS away_team,
            mr.full_time_home_goals,
            mr.full_time_away_goals
        FROM matchrecord mr
        INNER JOIN team home ON mr.home_team_id = home.team_id
        INNER JOIN team away ON mr.away_team_id = away.team_id
        WHERE mr.match_id = %s;
    """, (match_id,))

    match = cur.fetchone()

    # Match team stats
    cur.execute("""
    SELECT
        mts.is_home,
        t.team_id,
        t.team_name,
        t.team_logo,
        mts.goals,
        mts.shots,
        mts.shots_on_target,
        mts.corners,
        mts.fouls,
        mts.yellow_cards,
        mts.red_cards
    FROM matchteamstats mts
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
    season = request.args.get("season")
    team = request.args.get("team")
    opponent = request.args.get("opponent")

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            mr.match_date,
            s.season_name,
            home.team_name AS home_team,
            home.team_logo AS home_logo,
            away.team_name AS away_team,
            away.team_logo AS away_logo,
            p.home_win_probability,
            p.draw_probability,
            p.away_win_probability,
            p.predicted_result,
            p.actual_result
        FROM prediction p
        INNER JOIN matchrecord mr ON p.match_id = mr.match_id
        INNER JOIN season s ON mr.season_id = s.season_id
        INNER JOIN team home ON mr.home_team_id = home.team_id
        INNER JOIN team away ON mr.away_team_id = away.team_id
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

    query += " ORDER BY mr.match_date DESC;"

    cur.execute(query, params)
    predictions = cur.fetchall()

    cur.execute("SELECT season_name FROM season ORDER BY season_name;")
    seasons = cur.fetchall()

    cur.close()

    return render_template(
        "predictions.html",
        title="Predictions",
        predictions=predictions,
        seasons=seasons,
        selected_season=season,
        search_team=team,
        search_opponent=opponent
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