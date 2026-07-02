# PostgreSQL query helpers for the team and player insights dashboard.
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


_PLAYER_INSIGHT_BASE = """
    WITH team_membership AS (
        SELECT
            pts.player_id,
            pts.season_id,
            COUNT(DISTINCT pts.team_id) AS team_count,
            MIN(pts.team_id) AS team_id,
            STRING_AGG(DISTINCT t.team_name, ', ' ORDER BY t.team_name) AS team_name
        FROM player_team_season pts
        JOIN team t ON t.team_id = pts.team_id
        WHERE pts.season_id = %s
        GROUP BY pts.player_id, pts.season_id
    ),
    player_base AS (
        SELECT
            p.player_id,
            p.player_name,
            pos.position_name,
            tm.team_count,
            tm.team_id,
            tm.team_name,
            pss.appearances,
            COALESCE(pss.goals, 0) AS goals,
            COALESCE(pss.assists, 0) AS assists,
            COALESCE(pss.shots, 0) AS shots,
            COALESCE(pss.shots_on_target, 0) AS shots_on_target,
            COALESCE(pss.big_chances_created, 0) AS big_chances_created,
            COALESCE(pss.big_chances_missed, 0) AS big_chances_missed,
            COALESCE(pss.passes, 0) AS passes,
            COALESCE(pss.through_balls, 0) AS through_balls,
            COALESCE(pss.tackles, 0) AS tackles,
            COALESCE(pss.interceptions, 0) AS interceptions,
            COALESCE(pss.recoveries, 0) AS recoveries,
            COALESCE(pss.clearances, 0) AS clearances,
            COALESCE(pss.blocked_shots, 0) AS blocked_shots,
            COALESCE(pss.duels_won, 0) AS duels_won,
            COALESCE(pss.duels_lost, 0) AS duels_lost,
            COALESCE(pss.errors_leading_to_goal, 0) AS errors_leading_to_goal
        FROM player_season_stats pss
        JOIN player p ON p.player_id = pss.player_id
        JOIN position pos ON pos.position_id = pss.position_id
        LEFT JOIN team_membership tm
            ON tm.player_id = pss.player_id
           AND tm.season_id = pss.season_id
        WHERE pss.season_id = %s
    )
"""


def get_player_shot_efficiency(conn, season_id):
    query = _PLAYER_INSIGHT_BASE + """
        , shot_threshold AS (
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY shots) AS median_shots
            FROM player_base
            WHERE shots > 0
        ),
        shot_metrics AS (
            SELECT
                *,
                100.0 * goals::numeric / NULLIF(shots, 0) AS conversion_pct,
                100.0 * shots_on_target::numeric / NULLIF(shots, 0) AS accuracy_pct,
                100.0 * goals::numeric / NULLIF(shots_on_target, 0) AS on_target_conversion_pct
            FROM player_base
            WHERE shots >= (SELECT median_shots FROM shot_threshold)
              AND shots_on_target > 0
        ),
        ranked AS (
            SELECT
                *,
                PERCENT_RANK() OVER (ORDER BY conversion_pct) AS conversion_rank,
                PERCENT_RANK() OVER (ORDER BY accuracy_pct) AS accuracy_rank
            FROM shot_metrics
        )
        SELECT
            player_id,
            player_name,
            team_name,
            position_name,
            appearances,
            goals,
            shots,
            shots_on_target,
            ROUND(conversion_pct, 2) AS conversion_pct,
            ROUND(accuracy_pct, 2) AS accuracy_pct,
            ROUND(on_target_conversion_pct, 2) AS on_target_conversion_pct,
            ROUND((100.0 * (0.6 * conversion_rank + 0.4 * accuracy_rank))::numeric, 2)
                AS efficiency_index
        FROM ranked
        ORDER BY efficiency_index DESC, goals DESC, shots DESC
        LIMIT 20;
    """
    return _run_query(conn, query, (season_id, season_id))


def get_player_team_contribution(conn, season_id):
    query = _PLAYER_INSIGHT_BASE + """
        , team_attack AS (
            SELECT
                mts.team_id,
                COUNT(*) AS team_matches,
                SUM(mts.goals) AS team_goals
            FROM match_team_stats mts
            JOIN match_record mr ON mr.match_id = mts.match_id
            WHERE mr.season_id = %s
            GROUP BY mts.team_id
        ),
        contribution AS (
            SELECT
                pb.*,
                ta.team_matches,
                ta.team_goals,
                pb.goals + pb.assists AS goal_involvements,
                100.0 * (pb.goals + pb.assists)::numeric / NULLIF(ta.team_goals, 0)
                    AS involvement_share_pct,
                100.0 * pb.goals::numeric / NULLIF(ta.team_goals, 0) AS goal_share_pct
            FROM player_base pb
            JOIN team_attack ta ON ta.team_id = pb.team_id
            WHERE pb.team_count = 1
              AND pb.appearances >= CEIL(ta.team_matches * 0.5)
              AND ta.team_goals > 0
        ),
        ranked AS (
            SELECT
                *,
                RANK() OVER (
                    PARTITION BY team_id
                    ORDER BY involvement_share_pct DESC, goal_involvements DESC
                ) AS club_attack_rank
            FROM contribution
        )
        SELECT
            player_id,
            player_name,
            team_name,
            position_name,
            appearances,
            goals,
            assists,
            goal_involvements,
            team_goals,
            ROUND(goal_share_pct, 2) AS goal_share_pct,
            ROUND(involvement_share_pct, 2) AS involvement_share_pct,
            club_attack_rank
        FROM ranked
        ORDER BY involvement_share_pct DESC, goal_involvements DESC
        LIMIT 20;
    """
    return _run_query(conn, query, (season_id, season_id, season_id))


def get_player_creative_leverage(conn, season_id):
    query = _PLAYER_INSIGHT_BASE + """
        , chance_threshold AS (
            SELECT
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY big_chances_created)
                    AS median_chances
            FROM player_base
            WHERE big_chances_created > 0
        ),
        creative_metrics AS (
            SELECT
                *,
                1000.0 * big_chances_created::numeric / NULLIF(passes, 0)
                    AS chances_per_1000_passes,
                100.0 * assists::numeric / NULLIF(big_chances_created, 0) AS assist_yield_pct,
                through_balls::numeric / NULLIF(appearances, 0) AS through_balls_per_appearance
            FROM player_base
            WHERE big_chances_created >= (SELECT median_chances FROM chance_threshold)
              AND passes > 0
              AND appearances > 0
        ),
        ranked AS (
            SELECT
                *,
                PERCENT_RANK() OVER (ORDER BY chances_per_1000_passes) AS volume_rank,
                PERCENT_RANK() OVER (ORDER BY assist_yield_pct) AS yield_rank,
                PERCENT_RANK() OVER (ORDER BY through_balls_per_appearance) AS progression_rank
            FROM creative_metrics
        )
        SELECT
            player_id,
            player_name,
            team_name,
            position_name,
            appearances,
            assists,
            big_chances_created,
            through_balls,
            ROUND(chances_per_1000_passes, 2) AS chances_per_1000_passes,
            ROUND(assist_yield_pct, 2) AS assist_yield_pct,
            ROUND(through_balls_per_appearance, 2) AS through_balls_per_appearance,
            ROUND(
                (100.0 * (0.45 * volume_rank + 0.35 * yield_rank + 0.2 * progression_rank))::numeric,
                2
            ) AS creative_leverage_index
        FROM ranked
        ORDER BY creative_leverage_index DESC, big_chances_created DESC, assists DESC
        LIMIT 20;
    """
    return _run_query(conn, query, (season_id, season_id))


def get_player_defensive_influence(conn, season_id):
    query = _PLAYER_INSIGHT_BASE + """
        , defensive_pool AS (
            SELECT
                *,
                tackles + interceptions + recoveries + clearances + blocked_shots
                    AS defensive_actions
            FROM player_base
            WHERE position_name <> 'Goalkeeper'
              AND appearances > 0
              AND tackles + interceptions + recoveries + clearances + blocked_shots > 0
        ),
        appearance_threshold AS (
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY appearances) AS median_appearances
            FROM defensive_pool
        ),
        defensive_metrics AS (
            SELECT
                *,
                defensive_actions::numeric / NULLIF(appearances, 0)
                    AS actions_per_appearance,
                100.0 * duels_won::numeric / NULLIF(duels_won + duels_lost, 0)
                    AS duel_win_pct,
                errors_leading_to_goal::numeric / NULLIF(appearances, 0)
                    AS errors_per_appearance
            FROM defensive_pool
            WHERE appearances >= (SELECT median_appearances FROM appearance_threshold)
        ),
        ranked AS (
            SELECT
                *,
                PERCENT_RANK() OVER (ORDER BY actions_per_appearance) AS action_rank,
                PERCENT_RANK() OVER (ORDER BY duel_win_pct NULLS FIRST) AS duel_rank,
                PERCENT_RANK() OVER (ORDER BY errors_per_appearance DESC) AS reliability_rank
            FROM defensive_metrics
        )
        SELECT
            player_id,
            player_name,
            team_name,
            position_name,
            appearances,
            defensive_actions,
            duels_won,
            duels_lost,
            errors_leading_to_goal,
            ROUND(actions_per_appearance, 2) AS actions_per_appearance,
            ROUND(duel_win_pct, 2) AS duel_win_pct,
            ROUND(
                (100.0 * (0.55 * action_rank + 0.3 * duel_rank + 0.15 * reliability_rank))::numeric,
                2
            ) AS defensive_influence_index
        FROM ranked
        ORDER BY defensive_influence_index DESC, defensive_actions DESC
        LIMIT 20;
    """
    return _run_query(conn, query, (season_id, season_id))
