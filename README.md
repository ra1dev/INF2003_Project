# INF2003 Project

This project is a simple Flask web app for exploring football data. It lets users browse players, teams, matches, season summaries, and predictions in a clean web interface.

## What the app does

- Show player and team information
- Display match details and season recap pages
- Compare players and teams
- Support basic admin features for match notes and event annotations
- Use PostgreSQL for relational data and MongoDB for event-based data

## Quick start

1. Clone the repository.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install the required packages:

```powershell
pip install flask psycopg2 pymongo python-dotenv
```

4. Make sure your databases are available:
- PostgreSQL should be running, and the app expects a database named `epl_db_2`
- MongoDB should be running locally on `localhost:27017`

5. Update the database connection details in [Backend/db_conn.py](Backend/db_conn.py) if needed.

6. Start the app:

```powershell
python app.py
```

Then open: http://localhost:5000

## Project layout

- [app.py](app.py) – starts the Flask app
- [Backend/](Backend/) – routes, repositories, and database connections
- [Frontend/](Frontend/) – HTML templates and styles
- [data/](data/) – sample data used by the app
- [sql/](sql/) – SQL setup scripts

## Notes

- The app can run locally for testing without extra setup, but your database credentials may need to be adjusted.
- For the admin pages, the SQL scripts in [sql/](sql/) can be used to create the needed database tables.

