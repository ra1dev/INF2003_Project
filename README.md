# INF2003_Project
steps to setup flask:
1. clone git
2. in working directory, python -m venv venv
3. .\venv\Scripts\activate
4. pip install flask
5. pip install psycopg2
6. pip install pymongo
7. pip install python-dotenv
8. change password in db_conn.py

## Database CRUD setup

The admin pages demonstrate full CRUD in both databases:

- PostgreSQL Match Reports: `http://localhost:5000/admin/match-notes`
- MongoDB Event Annotation Studio: `http://localhost:5000/admin/event-annotations`

Install the MongoDB dependencies in the active virtual environment:

```powershell
pip install pymongo python-dotenv
```

Create the PostgreSQL table from the project root:

```powershell
psql -U postgres -d EPL_DB -f sql/admin_crud.sql
```

The application creates the MongoDB annotation indexes idempotently when the
collection is first used. They can also be created manually in `mongosh`:

```javascript
use("epl-db")
db.match_event_annotations.createIndex({ match_id: 1 })
db.match_event_annotations.createIndex({ match_id: 1, event_minute: 1 })
```

Set a private Flask session key before running the application outside local
development:

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
```
