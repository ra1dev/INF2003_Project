# Local MongoDB Import Bundle

Quick bundle to import StatsBomb EPL events into a local MongoDB instance.

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
- `data/statsbomb_to_app_match_map.csv`
- `data/matches_epl/` (matches JSON files) (used for mapping events only)
- `data/events_epl/` (event JSON files)


Example output document inside MongoDB

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

