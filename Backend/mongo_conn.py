import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

# Defaults are intentionally lightweight so the app can run locally without extra setup.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "epl-db")

_client = None
_db = None


def get_mongo_db():
    """Create a MongoDB client once and reuse it for subsequent database access."""
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        try:
            _client.server_info()
        except ServerSelectionTimeoutError as e:
            raise RuntimeError(f"Could not connect to MongoDB: {e}")
        _db = _client[MONGO_DB]
    return _db


def close_mongo():
    """Close the shared MongoDB client when the application is shutting down."""
    global _client
    if _client:
        _client.close()
        _client = None