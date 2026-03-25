import os
import bcrypt
import uuid
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

class Database:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("MONGO_URL") or os.getenv("DATABASE_URL")
        # Fallback to local if no URL provided
        if not self.db_url:
            self.db_url = "mongodb://localhost:27017/inkognito"
        
        self.client = MongoClient(self.db_url)
        # Handle both connection strings with DB name and without
        db_name = "inkognito"
        if "/" in self.db_url.split("://")[-1]:
            potential_db = self.db_url.split("/")[-1].split("?")[0]
            if potential_db:
                db_name = potential_db
        
        self.db = self.client[db_name]
        self._init_db()

    def _init_db(self):
        # Ensure indexes for performance and uniqueness
        self.db.users.create_index("username", unique=True)
        self.db.reports.create_index("report_id", unique=True)
        self.db.reports.create_index("user_id")

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _check_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    def register_user(self, username, password):
        password_hash = self._hash_password(password)
        user = {
            "username": username,
            "password_hash": password_hash,
            "created_at": datetime.utcnow()
        }
        try:
            result = self.db.users.insert_one(user)
            return str(result.inserted_id)
        except Exception:
            return None  # Username already exists

    def authenticate_user(self, username, password):
        user = self.db.users.find_one({"username": username})
        if user and self._check_password(password, user["password_hash"]):
            return {
                "id": str(user["_id"]),
                "username": user["username"]
            }
        return None

    def save_report_metadata(self, user_id, report_id, subject_name, generated_at, report_path):
        # Convert generated_at to datetime if it's a string
        if isinstance(generated_at, str):
            try:
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            except:
                dt = datetime.utcnow()
        else:
            dt = generated_at

        report = {
            "user_id": user_id,
            "report_id": report_id,
            "subject_name": subject_name,
            "generated_at": dt,
            "report_path": report_path
        }
        self.db.reports.insert_one(report)

    def get_user_reports(self, user_id):
        cursor = self.db.reports.find({"user_id": user_id}).sort("generated_at", -1)
        reports = []
        for doc in cursor:
            reports.append({
                "report_id": doc["report_id"],
                "subject_name": doc["subject_name"],
                "generated_at": doc["generated_at"].isoformat() if isinstance(doc["generated_at"], datetime) else doc["generated_at"],
                "report_path": doc["report_path"]
            })
        return reports

    def get_user_by_id(self, user_id):
        try:
            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return {
                    "id": str(user["_id"]),
                    "username": user["username"]
                }
        except:
            pass
        return None
