from config.database import db
from datetime import datetime
import uuid

class Session:
    @staticmethod
    def create_new_session(uid):
        session_id = str(uuid.uuid4())  # Generate a unique session ID
        new_session = {
            "uid": uid,
            "session_id": session_id,
            "images": [],
            "created_at": datetime.utcnow()
        }
        db.sessions.insert_one(new_session)
        return session_id

    @staticmethod
    def store_image(uid, session_id, image_url):
        db.sessions.update_one(
            {"uid": uid, "session_id": session_id},
            {"$push": {"images": image_url}}
        )

    @staticmethod
    def get_user_sessions(uid):
        sessions = db.sessions.find({"uid": uid}, {"_id": 0})  # Hide MongoDB _id
        return list(sessions)

    @staticmethod
    def delete_session(session_id):
        """
        Deletes the session from MongoDB along with all images linked to it.
        """
        session = db.sessions.find_one({"session_id": session_id})

        if not session:
            return False, "Session not found"

        # Delete all associated images
        db.images.delete_many({"session_id": session_id})

        # Delete session itself
        db.sessions.delete_one({"session_id": session_id})

        return True, "Session and associated images deleted successfully"