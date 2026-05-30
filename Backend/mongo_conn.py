import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "epl-db")

_client = None
_db = None

def get_mongo_db():
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
    global _client
    if _client:
        _client.close()
        _client = None