DROP VIEW IF EXISTS public.v_team_season_rankings;
DROP VIEW IF EXISTS public.v_team_season_summary;

CREATE VIEW public.v_team_season_summary AS
WITH team_match AS (
    SELECT
        t.team_id,
        t.team_name,
        COALESCE(
            t.team_logo,
            'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
            '&background=1e293b&color=ffffff&size=128'
        ) AS team_logo,
        s.season_id,
        s.season_name,
        mts.is_home,
        COALESCE(mts.goals, 0) AS team_goals,
        COALESCE(opponent_mts.goals, 0) AS opponent_goals,
        COALESCE(mts.shots, 0) AS shots,
        COALESCE(opponent_mts.shots, 0) AS opponent_shots,
        COALESCE(mts.shots_on_target, 0) AS shots_on_target,
        COALESCE(opponent_mts.shots_on_target, 0) AS opponent_shots_on_target,
        COALESCE(mts.corners, 0) AS corners,
        COALESCE(opponent_mts.corners, 0) AS opponent_corners,
        COALESCE(mts.fouls, 0) AS fouls,
        COALESCE(mts.yellow_cards, 0) AS yellow_cards,
        COALESCE(mts.red_cards, 0) AS red_cards
    FROM public.match_team_stats mts
    INNER JOIN public.match_team_stats opponent_mts
        ON mts.match_id = opponent_mts.match_id
       AND mts.is_home <> opponent_mts.is_home
    INNER JOIN public.match_record mr
        ON mts.match_id = mr.match_id
    INNER JOIN public.team t
        ON mts.team_id = t.team_id
    INNER JOIN public.season s
        ON mr.season_id = s.season_id
),
team_season_totals AS (
    SELECT
        team_id,
        team_name,
        team_logo,
        season_id,
        season_name,
        COUNT(*)::integer AS matches_played,
        COUNT(*) FILTER (WHERE team_goals > opponent_goals)::integer AS wins,
        COUNT(*) FILTER (WHERE team_goals = opponent_goals)::integer AS draws,
        COUNT(*) FILTER (WHERE team_goals < opponent_goals)::integer AS losses,
        SUM(
            CASE
                WHEN team_goals > opponent_goals THEN 3
                WHEN team_goals = opponent_goals THEN 1
                ELSE 0
            END
        )::integer AS points,
        SUM(team_goals)::integer AS goals_for,
        SUM(opponent_goals)::integer AS goals_against,
        (SUM(team_goals) - SUM(opponent_goals))::integer AS goal_difference,
        SUM(shots)::integer AS shots,
        SUM(opponent_shots)::integer AS shots_allowed,
        (SUM(shots) - SUM(opponent_shots))::integer AS shot_difference,
        SUM(shots_on_target)::integer AS shots_on_target,
        SUM(opponent_shots_on_target)::integer AS shots_on_target_allowed,
        (SUM(shots_on_target) - SUM(opponent_shots_on_target))::integer AS shots_on_target_difference,
        SUM(corners)::integer AS corners,
        SUM(opponent_corners)::integer AS corners_allowed,
        (SUM(corners) - SUM(opponent_corners))::integer AS corner_difference,
        SUM(fouls)::integer AS fouls,
        SUM(yellow_cards)::integer AS yellow_cards,
        SUM(red_cards)::integer AS red_cards,
        COUNT(*) FILTER (WHERE opponent_goals = 0)::integer AS clean_sheets,
        COUNT(*) FILTER (WHERE team_goals = 0)::integer AS failed_to_score,
        COUNT(*) FILTER (WHERE is_home)::integer AS home_matches,
        COUNT(*) FILTER (WHERE is_home AND team_goals > opponent_goals)::integer AS home_wins,
        COUNT(*) FILTER (WHERE is_home AND team_goals = opponent_goals)::integer AS home_draws,
        COUNT(*) FILTER (WHERE is_home AND team_goals < opponent_goals)::integer AS home_losses,
        SUM(
            CASE
                WHEN is_home AND team_goals > opponent_goals THEN 3
                WHEN is_home AND team_goals = opponent_goals THEN 1
                ELSE 0
            END
        )::integer AS home_points,
        SUM(team_goals) FILTER (WHERE is_home)::integer AS home_goals_for,
        SUM(opponent_goals) FILTER (WHERE is_home)::integer AS home_goals_against,
        COUNT(*) FILTER (WHERE NOT is_home)::integer AS away_matches,
        COUNT(*) FILTER (WHERE NOT is_home AND team_goals > opponent_goals)::integer AS away_wins,
        COUNT(*) FILTER (WHERE NOT is_home AND team_goals = opponent_goals)::integer AS away_draws,
        COUNT(*) FILTER (WHERE NOT is_home AND team_goals < opponent_goals)::integer AS away_losses,
        SUM(
            CASE
                WHEN NOT is_home AND team_goals > opponent_goals THEN 3
                WHEN NOT is_home AND team_goals = opponent_goals THEN 1
                ELSE 0
            END
        )::integer AS away_points,
        SUM(team_goals) FILTER (WHERE NOT is_home)::integer AS away_goals_for,
        SUM(opponent_goals) FILTER (WHERE NOT is_home)::integer AS away_goals_against
    FROM team_match
    GROUP BY
        team_id,
        team_name,
        team_logo,
        season_id,
        season_name
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
FROM team_season_totals;

CREATE VIEW public.v_team_season_rankings AS
SELECT
    v.*,
    COUNT(*) OVER (PARTITION BY season_id)::integer AS teams_in_season,
    ROW_NUMBER() OVER (
        PARTITION BY season_id
        ORDER BY points DESC, goal_difference DESC, goals_for DESC, team_name ASC
    )::integer AS league_position,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY points_per_match DESC, goal_difference_per_match DESC, goals_per_match DESC
    )::integer AS points_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY goals_per_match DESC, goal_conversion_pct DESC NULLS LAST, shots_on_target_per_match DESC
    )::integer AS attack_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY goals_conceded_per_match ASC, clean_sheet_rate_pct DESC, shots_on_target_allowed_per_match ASC
    )::integer AS defense_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY shot_share_pct DESC NULLS LAST, shot_difference_per_match DESC, shots_per_match DESC
    )::integer AS pressure_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY home_points_per_match DESC, home_win_rate_pct DESC, home_goals_for DESC
    )::integer AS home_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY away_points_per_match DESC, away_win_rate_pct DESC, away_goals_for DESC
    )::integer AS away_rank,
    RANK() OVER (
        PARTITION BY season_id
        ORDER BY discipline_score_per_match ASC, red_cards ASC, yellow_cards ASC
    )::integer AS discipline_rank
FROM public.v_team_season_summary v;
