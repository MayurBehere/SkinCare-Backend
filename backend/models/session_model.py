from config.database import db
from datetime import datetime
import uuid

class Session:

    @staticmethod
    def store_image(uid, session_id, image_url):
        db.sessions.update_one(
            {"uid": uid, "session_id": session_id},
            {"$push": {"images": image_url}}
        )

    @staticmethod
    def create_session(uid, session_id, session_name):
        """Create a new session with a name."""
        db.sessions.insert_one({
            "uid": uid,
            "session_id": session_id,
            "session_name": session_name,  # Make sure this is saved
            "images": [],
            "created_at": datetime.now()
        })
        return session_id

    @staticmethod
    def get_user_sessions(uid):
        """Get all sessions for a user including session names."""
        sessions = list(db.sessions.find(
            {"uid": uid},
            {"_id": 0, "uid": 1, "session_id": 1, "session_name": 1, "created_at": 1}  # Include session_name
        ))
        
        # Debug output
        print(f"Retrieved sessions for {uid}: {sessions}")
        
        return sessions

    @staticmethod
    def delete_session(session_id):
        """Delete a session by ID."""
        result = db.sessions.delete_one({"session_id": session_id})
        if result.deleted_count > 0:
            return True, "Session deleted successfully"
        return False, "Session not found"
    
    @staticmethod
    def add_images_to_session(uid, session_id, image_urls):
        if not uid or not session_id or not image_urls:
            return False, "Missing parameters"

        try:
            # Make sure this matches your collection schema
            result = db.sessions.update_one(
                {"uid": uid, "session_id": session_id},
                {"$push": {"images": {"$each": image_urls}}}
            )

            if result.matched_count == 0:
                return False, "Session not found"
            
            return True, "Images added successfully"
        except Exception as e:
            print("❌ DB Error in add_images_to_session:", str(e))
            return False, f"Internal server error: {str(e)}"
        
        