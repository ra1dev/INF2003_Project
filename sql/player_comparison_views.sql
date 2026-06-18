DROP VIEW IF EXISTS public.v_player_season_rankings;
DROP VIEW IF EXISTS public.v_player_season_summary;

CREATE VIEW public.v_player_season_summary AS
WITH player_clubs AS (
    SELECT
        pts.player_id,
        pts.season_id,
        STRING_AGG(DISTINCT t.team_name, ', ' ORDER BY t.team_name) AS club_names,
        COUNT(DISTINCT t.team_id)::integer AS club_count
    FROM public.player_team_season pts
    INNER JOIN public.team t
        ON pts.team_id = t.team_id
    GROUP BY
        pts.player_id,
        pts.season_id
)
SELECT
    p.player_id,
    p.player_name,
    p.normalized_player_name,
    p.player_image,
    p.player_photo_url,
    COALESCE(p.player_image, p.player_photo_url) AS image_url,
    s.season_id,
    s.season_name,
    pos.position_id,
    pos.position_name,
    LOWER(pos.position_name) AS position_group,
    COALESCE(pc.club_names, 'Unknown Team') AS club_names,
    COALESCE(pc.club_count, 0) AS club_count,
    pss.appearances,
    pss.clean_sheets,
    pss.goals_conceded,
    pss.tackles,
    pss.tackle_success_pct,
    pss.last_man_tackles,
    pss.blocked_shots,
    pss.interceptions,
    pss.clearances,
    pss.headed_clearances,
    pss.clearances_off_line,
    pss.recoveries,
    pss.duels_won,
    pss.duels_lost,
    pss.successful_50_50s,
    pss.aerial_battles_won,
    pss.aerial_battles_lost,
    pss.own_goals,
    pss.errors_leading_to_goal,
    pss.assists,
    pss.passes,
    pss.big_chances_created,
    pss.crosses,
    pss.cross_accuracy_pct,
    pss.through_balls,
    pss.accurate_long_balls,
    pss.yellow_cards,
    pss.red_cards,
    pss.fouls,
    pss.offsides,
    pss.goals,
    pss.headed_goals,
    pss.goals_with_right_foot,
    pss.goals_with_left_foot,
    pss.hit_woodwork,
    pss.penalties_scored,
    pss.freekicks_scored,
    pss.shots,
    pss.shots_on_target,
    pss.shooting_accuracy_pct,
    pss.big_chances_missed,
    pss.saves,
    pss.penalties_saved,
    pss.punches,
    pss.high_claims,
    pss.catches,
    pss.sweeper_clearances,
    pss.throw_outs,
    pss.goal_kicks,
    CASE
        WHEN pss.goals IS NULL AND pss.assists IS NULL THEN NULL
        ELSE COALESCE(pss.goals, 0) + COALESCE(pss.assists, 0)
    END AS goal_contributions,
    CASE
        WHEN pss.yellow_cards IS NULL AND pss.red_cards IS NULL THEN NULL
        ELSE COALESCE(pss.yellow_cards, 0) + COALESCE(pss.red_cards, 0)
    END AS cards,
    ROUND(pss.goals::numeric / NULLIF(pss.appearances, 0), 3) AS goals_per_appearance,
    ROUND(pss.assists::numeric / NULLIF(pss.appearances, 0), 3) AS assists_per_appearance,
    ROUND((COALESCE(pss.goals, 0) + COALESCE(pss.assists, 0))::numeric / NULLIF(pss.appearances, 0), 3) AS goal_contributions_per_appearance,
    ROUND(pss.yellow_cards::numeric / NULLIF(pss.appearances, 0), 3) AS yellow_cards_per_appearance,
    ROUND(pss.red_cards::numeric / NULLIF(pss.appearances, 0), 3) AS red_cards_per_appearance,
    ROUND((COALESCE(pss.yellow_cards, 0) + COALESCE(pss.red_cards, 0))::numeric / NULLIF(pss.appearances, 0), 3) AS cards_per_appearance,
    ROUND(pss.fouls::numeric / NULLIF(pss.appearances, 0), 3) AS fouls_per_appearance,
    ROUND(pss.shots::numeric / NULLIF(pss.appearances, 0), 3) AS shots_per_appearance,
    ROUND(pss.shots_on_target::numeric / NULLIF(pss.appearances, 0), 3) AS shots_on_target_per_appearance,
    ROUND(pss.goals::numeric / NULLIF(pss.shots, 0) * 100, 2) AS goal_conversion_pct,
    ROUND(pss.passes::numeric / NULLIF(pss.appearances, 0), 3) AS passes_per_appearance,
    ROUND(pss.big_chances_created::numeric / NULLIF(pss.appearances, 0), 3) AS big_chances_created_per_appearance,
    ROUND(pss.crosses::numeric / NULLIF(pss.appearances, 0), 3) AS crosses_per_appearance,
    ROUND(pss.tackles::numeric / NULLIF(pss.appearances, 0), 3) AS tackles_per_appearance,
    ROUND(pss.interceptions::numeric / NULLIF(pss.appearances, 0), 3) AS interceptions_per_appearance,
    ROUND(pss.clearances::numeric / NULLIF(pss.appearances, 0), 3) AS clearances_per_appearance,
    ROUND(pss.blocked_shots::numeric / NULLIF(pss.appearances, 0), 3) AS blocked_shots_per_appearance,
    ROUND(pss.clean_sheets::numeric / NULLIF(pss.appearances, 0), 3) AS clean_sheets_per_appearance,
    ROUND(pss.saves::numeric / NULLIF(pss.appearances, 0), 3) AS saves_per_appearance,
    ROUND(pss.goals_conceded::numeric / NULLIF(pss.appearances, 0), 3) AS goals_conceded_per_appearance
FROM public.player_season_stats pss
INNER JOIN public.player p
    ON pss.player_id = p.player_id
INNER JOIN public.season s
    ON pss.season_id = s.season_id
INNER JOIN public.position pos
    ON pss.position_id = pos.position_id
LEFT JOIN player_clubs pc
    ON pss.player_id = pc.player_id
   AND pss.season_id = pc.season_id;

CREATE VIEW public.v_player_season_rankings AS
WITH eligible AS (
    SELECT *
    FROM public.v_player_season_summary
    WHERE appearances >= 5
),
role_scores AS (
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
        END AS role_score
    FROM eligible
),
ranks AS (
    SELECT
        player_id,
        season_id,
        RANK() OVER (
            PARTITION BY season_id
            ORDER BY appearances DESC, player_name ASC
        )::integer AS appearance_rank,
        RANK() OVER (
            PARTITION BY season_id
            ORDER BY goal_contributions DESC NULLS LAST, goals DESC NULLS LAST, assists DESC NULLS LAST, player_name ASC
        )::integer AS goal_contribution_rank,
        RANK() OVER (
            PARTITION BY season_id
            ORDER BY goal_contributions_per_appearance DESC NULLS LAST, goal_contributions DESC NULLS LAST, player_name ASC
        )::integer AS goal_contribution_rate_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY appearances DESC, player_name ASC
        )::integer AS position_appearance_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY role_score DESC NULLS LAST, appearances DESC, player_name ASC
        )::integer AS position_role_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY goals DESC NULLS LAST, player_name ASC
        )::integer AS position_goals_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY assists DESC NULLS LAST, player_name ASC
        )::integer AS position_assists_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY tackles DESC NULLS LAST, player_name ASC
        )::integer AS position_tackles_rank,
        RANK() OVER (
            PARTITION BY season_id, position_id
            ORDER BY saves DESC NULLS LAST, player_name ASC
        )::integer AS position_saves_rank
    FROM role_scores
)
SELECT
    v.*,
    r.appearance_rank,
    r.goal_contribution_rank,
    r.goal_contribution_rate_rank,
    r.position_appearance_rank,
    r.position_role_rank,
    r.position_goals_rank,
    r.position_assists_rank,
    r.position_tackles_rank,
    r.position_saves_rank
FROM public.v_player_season_summary v
LEFT JOIN ranks r
    ON v.player_id = r.player_id
   AND v.season_id = r.season_id;
