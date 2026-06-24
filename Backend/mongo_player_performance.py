from __future__ import annotations

from collections import defaultdict, Counter
from typing import Any


def _get_location_grid_cell(location: list | None, grid_size: int = 20) -> tuple[int, int] | None:
    """Convert xy coordinates to grid cell. Pitch is roughly 120x80."""
    if not location or len(location) < 2:
        return None
    x, y = location[0], location[1]
    # Clamp to pitch boundaries
    x = max(0, min(x, 120))
    y = max(0, min(y, 80))
    grid_x = int((x / 120) * grid_size)
    grid_y = int((y / 80) * grid_size)
    return (min(grid_x, grid_size - 1), min(grid_y, grid_size - 1))


def _get_period_bin(minute: int | None) -> str:
    """Bin minutes into periods: 0-20, 21-40, 41-60, 61-80, 81+."""
    if minute is None:
        return "unknown"
    if minute <= 20:
        return "0-20"
    elif minute <= 40:
        return "21-40"
    elif minute <= 60:
        return "41-60"
    elif minute <= 80:
        return "61-80"
    else:
        return "81+"


def build_player_performance(
    events: list[dict[str, Any]],
    match: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Build a denormalized player performance document for each player in the match.
    Returns a list of player performance docs, one per player.
    """
    match = match or {}
    home_team = match.get("home_team")
    away_team = match.get("away_team")

    player_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    player_info: dict[str, dict[str, Any]] = {}

    # Group events by player
    for event in events:
        if not isinstance(event, dict):
            continue

        player = event.get("player") or {}
        player_id = player.get("id")
        player_name = player.get("name")
        team = event.get("team") or {}
        team_name = team.get("name")

        if not player_id or not player_name:
            continue

        key = f"{player_id}_{player_name}"
        player_events[key].append(event)

        if key not in player_info:
            player_info[key] = {
                "player_id": player_id,
                "player_name": player_name,
                "team_name": team_name,
                "is_home": team_name == home_team,
            }

    player_docs = []

    for player_key, events_list in player_events.items():
        if not events_list:
            continue

        info = player_info[player_key]
        doc = _build_single_player_performance(events_list, match, info)
        player_docs.append(doc)

    return player_docs


def _build_single_player_performance(
    events: list[dict[str, Any]],
    match: dict[str, Any],
    player_info: dict[str, Any],
) -> dict[str, Any]:
    """Build a single player's performance document."""
    player_name = player_info["player_name"]
    player_id = player_info["player_id"]
    team_name = player_info["team_name"]

    # Heatmap
    heatmap_grid: dict[tuple[int, int], int] = defaultdict(int)

    # Passing network
    passes_made: dict[str, dict[str, int]] = defaultdict(lambda: {"passes": 0, "successful": 0})
    passes_received_from: dict[str, dict[str, int]] = defaultdict(
        lambda: {"passes": 0, "successful": 0}
    )

    # Statistics
    stats = {
        "touches": 0,
        "passes": 0,
        "passes_completed": 0,
        "shots": 0,
        "shots_on_target": 0,
        "fouls": 0,
        "cards": {"yellow": 0, "red": 0},
        "tackles": 0,
        "interceptions": 0,
        "distance_meters": 0,
        "xg": 0,
    }

    # Period breakdown
    period_breakdown: dict[str, dict[str, int]] = defaultdict(
        lambda: {"touches": 0, "passes": 0, "passes_completed": 0}
    )

    # Action sequence for narrative
    actions: list[dict[str, Any]] = []

    for event in events:
        if not isinstance(event, dict):
            continue

        event_type = event.get("type") or {}
        event_type_name = event_type.get("name")
        minute = event.get("minute")
        timestamp = event.get("timestamp")
        location = event.get("location")
        period_bin = _get_period_bin(minute)

        # Record location for heatmap
        if location:
            grid_cell = _get_location_grid_cell(location)
            if grid_cell:
                heatmap_grid[grid_cell] += 1
            stats["touches"] += 1
            period_breakdown[period_bin]["touches"] += 1

        # Track actions
        action_entry = {
            "timestamp": timestamp or f"{minute or 0}:00",
            "type": event_type_name,
            "period": period_bin,
        }

        if event_type_name == "Pass":
            pass_event = event.get("pass") or {}
            recipient = (pass_event.get("recipient") or {}).get("name")
            outcome = (pass_event.get("outcome") or {}).get("name")
            length = pass_event.get("length")

            stats["passes"] += 1
            period_breakdown[period_bin]["passes"] += 1

            if outcome != "Incomplete":
                stats["passes_completed"] += 1
                period_breakdown[period_bin]["passes_completed"] += 1

            if recipient:
                passes_made[recipient]["passes"] += 1
                if outcome != "Incomplete":
                    passes_made[recipient]["successful"] += 1

            action_entry["recipient"] = recipient
            action_entry["outcome"] = outcome
            if length:
                action_entry["length"] = length
                stats["distance_meters"] += length

        elif event_type_name == "Shot":
            shot_event = event.get("shot") or {}
            outcome = (shot_event.get("outcome") or {}).get("name")
            xg = shot_event.get("statsbomb_xg")

            stats["shots"] += 1
            if outcome in {"Goal", "Saved", "On Target"}:
                stats["shots_on_target"] += 1

            if xg:
                stats["xg"] += xg

            action_entry["outcome"] = outcome
            if xg:
                action_entry["xg"] = xg

        elif event_type_name == "Tackle":
            tackle_event = event.get("tackle") or {}
            outcome = (tackle_event.get("outcome") or {}).get("name")
            stats["tackles"] += 1
            action_entry["outcome"] = outcome

        elif event_type_name == "Interception":
            stats["interceptions"] += 1

        elif event_type_name == "Foul Committed":
            foul_event = event.get("foul_committed") or {}
            card = (foul_event.get("card") or {}).get("name")
            stats["fouls"] += 1
            if card:
                if card == "Yellow Card":
                    stats["cards"]["yellow"] += 1
                elif card == "Red Card":
                    stats["cards"]["red"] += 1
                action_entry["card"] = card

        actions.append(action_entry)

    # Convert heatmap to list format
    heatmap_list = []
    for y in range(20):
        row = []
        for x in range(20):
            row.append(heatmap_grid.get((x, y), 0))
        heatmap_list.append(row)

    # Build passing network
    passing_network = []
    for recipient, pass_data in sorted(passes_made.items()):
        if pass_data["passes"] >= 2:  # Only include if at least 2 passes
            accuracy = (
                (pass_data["successful"] / pass_data["passes"] * 100)
                if pass_data["passes"]
                else 0
            )
            passing_network.append(
                {
                    "recipient": recipient,
                    "passes": pass_data["passes"],
                    "successful": pass_data["successful"],
                    "accuracy_pct": round(accuracy, 1),
                }
            )

    passing_network = sorted(passing_network, key=lambda x: x["passes"], reverse=True)[:10]

    # Pass accuracy
    pass_accuracy = (
        (stats["passes_completed"] / stats["passes"] * 100) if stats["passes"] else 0
    )

    # Shot accuracy
    shot_accuracy = (stats["shots_on_target"] / stats["shots"] * 100) if stats["shots"] else 0

    return {
        "app_match_id": None,  # Will be set by importer
        "statsbomb_match_id": None,  # Will be set by importer
        "player_id": player_id,
        "player_name": player_name,
        "team_name": team_name,
        "match_date": None,  # Will be set by importer
        "statistics": {
            "touches": stats["touches"],
            "passes": stats["passes"],
            "passes_completed": stats["passes_completed"],
            "pass_accuracy_pct": round(pass_accuracy, 1),
            "shots": stats["shots"],
            "shots_on_target": stats["shots_on_target"],
            "shot_accuracy_pct": round(shot_accuracy, 1),
            "fouls": stats["fouls"],
            "tackles": stats["tackles"],
            "interceptions": stats["interceptions"],
            "yellow_cards": stats["cards"]["yellow"],
            "red_cards": stats["cards"]["red"],
            "distance_meters": round(stats["distance_meters"], 1),
            "xg": round(stats["xg"], 2),
        },
        "heatmap": heatmap_list,
        "passing_network": passing_network,
        "period_breakdown": {
            period: {
                "touches": data["touches"],
                "passes": data["passes"],
                "passes_completed": data["passes_completed"],
            }
            for period, data in sorted(period_breakdown.items())
        },
        "actions": actions,
    }
