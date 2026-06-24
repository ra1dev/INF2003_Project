# Local MongoDB Import Bundle

Quick bundle to import StatsBomb EPL events into a local MongoDB instance.
Data sourced from https://github.com/statsbomb/open-data

Download MongoDB:
https://www.mongodb.com/try/download/community

Requirements
- Python 3.10+
- MongoDB running on `127.0.0.1:27017`

Install
```powershell
pip install -r requirements.txt
```

Quick checks
```powershell
mongosh "mongodb://127.0.0.1:27017"
Test-NetConnection 127.0.0.1 -Port 27017
```

Dry-run (safe)
```powershell
python import_to_local_mongodb.py --dry-run --match-id 3754217
```

Import (drop DB first)
```powershell
python import_to_local_mongodb.py --reset-db
```

Files included
- `data/statsbomb_to_app_match_map.csv` (maps statsbomb match events to existing PostgreSQL matches table)
- `data/matches_epl/` (used for getting match events from EPL matches only)
- `data/events_epl/` (match events JSON files)


Example MATCH EVENT output document inside MongoDB

```json
{
	"app_match_id": 123,
	"statsbomb_match_id": 3895302,
	"competition_id": 2,
	"season": "2023/24",
	"home_team": "Arsenal",
	"away_team": "Chelsea",
	"events": [
		{
			"type": "pass",
			"timestamp": "2023-08-12T15:00:00Z",
			"minute": 12,
			"second": 34,
			"team": "Arsenal",
			"player": "Bukayo Saka",
			"position": { "x": 40.5, "y": 25.2 },
			"pass_end_location": { "x": 52.3, "y": 30.1 }
		}
	],
	"imported_at": "2026-05-30T12:34:56Z"
}
```

Example PLAYER MATCH PERFORMANCE output document inside MongoDB

```json

{
  "app_match_id": 123,
  "statsbomb_match_id": 3895302,
  "player_id": 22084,
  "player_name": "Bukayo Saka",
  "team_name": "Arsenal",
  "match_date": null,

  "statistics": {
    "touches": 58,
    "passes": 36,
    "passes_completed": 30,
    "pass_accuracy_pct": 83.3,
    "shots": 3,
    "shots_on_target": 1,
    "shot_accuracy_pct": 33.3,
    "fouls": 1,
    "tackles": 2,
    "interceptions": 1,
    "yellow_cards": 0,
    "red_cards": 0,
    "distance_meters": 612.4,
    "xg": 0.27
  },

  "heatmap": [
    [0, 0, 0, 0, 0],
    [0, 1, 3, 2, 0],
    [0, 0, 4, 1, 0]
  ],

  "passing_network": [
    {
      "recipient": "Martin Odegaard",
      "passes": 8,
      "successful": 7,
      "accuracy_pct": 87.5
    },
    {
      "recipient": "Ben White",
      "passes": 5,
      "successful": 5,
      "accuracy_pct": 100.0
    }
  ],

  "period_breakdown": {
    "0-20": {
      "touches": 12,
      "passes": 8,
      "passes_completed": 7
    },
    "21-40": {
      "touches": 10,
      "passes": 6,
      "passes_completed": 5
    }
  },

  "actions": [
    {
      "timestamp": "00:12:34",
      "type": "Pass",
      "period": "0-20",
      "recipient": "Martin Odegaard",
      "outcome": null,
      "length": 14.2
    },
    {
      "timestamp": "00:34:10",
      "type": "Shot",
      "period": "21-40",
      "outcome": "Saved",
      "xg": 0.12
    }
  ]
}

```

