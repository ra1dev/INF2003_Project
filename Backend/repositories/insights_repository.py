from psycopg2.extras import RealDictCursor

def _run_query(conn, query, params=None):
    """Execute a parameterized query and return RealDictCursor results."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params or ())
        return cur.fetchall()


def get_seasons(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT season_id, season_name
            FROM season
            ORDER BY start_year DESC
        """)
        return cur.fetchall()

#common table expression for the others to work on
def get_team_season_summary(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,

                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,

                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,

                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,

                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,

                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,

                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT *
        FROM team_season_summary;
    """

    return _run_query(conn, query, (season_id,))

#goals / shots * 100 (shot conversion)
def get_clinical_finishing(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,

                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,

                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,

                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,

                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,

                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,

                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            goals_scored,
            shots,
            ROUND(100.0 * goals_scored::numeric / NULLIF(shots, 0), 2) AS clinical_finishing_pct
        FROM team_season_summary
        WHERE shots > 0
        ORDER BY clinical_finishing_pct DESC, goals_scored DESC;
    """

    return _run_query(conn, query, (season_id,))

#shots_on_target / shots * 100
def get_shot_accuracy(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            shots,
            shots_on_target,
            ROUND(100.0 * shots_on_target::numeric / NULLIF(shots, 0), 2) AS shot_accuracy_pct
        FROM team_season_summary
        WHERE shots > 0
        ORDER BY shot_accuracy_pct DESC, shots_on_target DESC;
    """

    return _run_query(conn, query, (season_id,))

#home_points / home_matches
def get_home_dominance(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            home_matches,
            home_points,
            home_goals_scored,
            home_goals_conceded,
            ROUND(home_points::numeric / NULLIF(home_matches, 0), 2) AS home_points_per_match
        FROM team_season_summary
        WHERE home_matches > 0
        ORDER BY home_points_per_match DESC, home_points DESC;
    """

    return _run_query(conn, query, (season_id,))

#away_points / away_matches
def get_away_resilience(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            away_matches,
            away_points,
            away_goals_scored,
            away_goals_conceded,
            ROUND(away_points::numeric / NULLIF(away_matches, 0), 2) AS away_points_per_match
        FROM team_season_summary
        WHERE away_matches > 0
        ORDER BY away_points_per_match DESC, away_points DESC;
    """

    return _run_query(conn, query, (season_id,))

#(yellow_cards + (red_cards × 2)) / matches_played
def get_discipline_risk(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            matches_played,
            yellow_cards,
            red_cards,
            ROUND(yellow_cards::numeric / NULLIF(matches_played, 0), 2) AS yellow_cards_per_match,
            ROUND(red_cards::numeric / NULLIF(matches_played, 0), 2) AS red_cards_per_match,
            ROUND((yellow_cards + red_cards * 2)::numeric / NULLIF(matches_played, 0), 2) AS discipline_risk_score
        FROM team_season_summary
        WHERE matches_played > 0
        ORDER BY discipline_risk_score DESC, red_cards DESC, yellow_cards DESC;
    """

    return _run_query(conn, query, (season_id,))

#high shots per match, low conversion
def get_pressure_without_payoff(conn, season_id, min_shots=100):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            matches_played,
            shots,
            goals_scored,
            ROUND(shots::numeric / NULLIF(matches_played, 0), 2) AS shots_per_match,
            ROUND(100.0 * goals_scored::numeric / NULLIF(shots, 0), 2) AS conversion_pct,
            ROUND(
                (shots::numeric / NULLIF(matches_played, 0))
                / NULLIF((goals_scored::numeric / NULLIF(shots, 0)), 0),
                2
            ) AS pressure_without_payoff_score
        FROM team_season_summary
        WHERE matches_played > 0
          AND shots >= %s
        ORDER BY shots_per_match DESC, conversion_pct ASC;
    """

    return _run_query(conn, query, (season_id, min_shots))

#goals_conceded per match (low is better)
def get_defensive_resistance(conn, season_id):
    query = """
        WITH team_season_summary AS (
            SELECT
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name,
                COUNT(*) AS matches_played,
                COUNT(*) FILTER (WHERE mts.is_home) AS home_matches,
                COUNT(*) FILTER (WHERE NOT mts.is_home) AS away_matches,
                SUM(mts.goals) AS goals_scored,
                SUM(opp.goals) AS goals_conceded,
                SUM(mts.shots) AS shots,
                SUM(mts.shots_on_target) AS shots_on_target,
                SUM(mts.yellow_cards) AS yellow_cards,
                SUM(mts.red_cards) AS red_cards,
                SUM(mts.goals) FILTER (WHERE mts.is_home) AS home_goals_scored,
                SUM(opp.goals) FILTER (WHERE mts.is_home) AS home_goals_conceded,
                SUM(mts.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_scored,
                SUM(opp.goals) FILTER (WHERE NOT mts.is_home) AS away_goals_conceded,
                SUM(
                    CASE
                        WHEN mts.goals > opp.goals THEN 3
                        WHEN mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                SUM(
                    CASE
                        WHEN mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS home_points,
                SUM(
                    CASE
                        WHEN NOT mts.is_home AND mts.goals > opp.goals THEN 3
                        WHEN NOT mts.is_home AND mts.goals = opp.goals THEN 1
                        ELSE 0
                    END
                ) AS away_points
            FROM match_team_stats mts
            JOIN match_team_stats opp
                ON opp.match_id = mts.match_id
               AND opp.team_id <> mts.team_id
            JOIN team t
                ON t.team_id = mts.team_id
            JOIN match_record mr
                ON mr.match_id = mts.match_id
            JOIN season s
                ON s.season_id = mr.season_id
            WHERE s.season_id = %s
            GROUP BY
                s.season_id,
                s.season_name,
                t.team_id,
                t.team_name
        )
        SELECT
            team_id,
            team_name,
            matches_played,
            goals_conceded,
            ROUND(goals_conceded::numeric / NULLIF(matches_played, 0), 2) AS goals_conceded_per_match
        FROM team_season_summary
        WHERE matches_played > 0
        ORDER BY goals_conceded_per_match ASC, goals_conceded ASC;
    """

    return _run_query(conn, query, (season_id,))
