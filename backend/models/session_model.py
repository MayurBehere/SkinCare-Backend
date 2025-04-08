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
            "session_name": session_name,
            "images": [],
            "classification_results": None,
            "created_at": datetime.now()
        })
        return session_id

    @staticmethod
    def get_user_sessions(uid):
        """Get all sessions for a user including session names."""
        sessions = list(db.sessions.find(
            {"uid": uid},
            {
                "_id": 0,
                "uid": 1,
                "session_id": 1,
                "session_name": 1,
                "created_at": 1,
                "images": 1,
                "classification_results": 1
            }
        ))
        print(f"Retrieved sessions for {uid}: {sessions}")
        return sessions

    @staticmethod
    def get_session_by_id(session_id):
        """Get a single session by its ID."""
        session = db.sessions.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        print(f"Fetched session for session_id {session_id}: {session}")
        return session

    @staticmethod
    def delete_session(session_id):
        """Delete a session by ID."""
        result = db.sessions.delete_one({"session_id": session_id})
        if result.deleted_count > 0:
            return True, "Session deleted successfully"
        return False, "Session not found"

    @staticmethod
    def add_images_to_session(uid, session_id, image_object):
        """
        Add a single image object (dict with url + delete_url) to the session.
        """
        if not uid or not session_id or not image_object:
            return False, "Missing parameters"

        if not isinstance(image_object, dict) or "url" not in image_object or "delete_url" not in image_object:
            print("⚠️ image_object must be a dict with 'url' and 'delete_url'")
            return False, "Invalid image format"

        try:
            result = db.sessions.update_one(
                {"uid": uid, "session_id": session_id},
                {"$push": {"images": image_object}}
            )

            if result.matched_count == 0:
                return False, "Session not found"

            return True, "Image added successfully"
        except Exception as e:
            print("❌ DB Error in add_images_to_session:", str(e))
            return False, f"Internal server error: {str(e)}"

    @staticmethod
    def update_classification_results(session_id, classification_results):
        try:
            if not isinstance(classification_results, dict):
                return False, "Invalid classification result format"

            print(f"[📝] Updating session {session_id} with result: {classification_results}")

            results_data = {
                "acne_type": classification_results.get("acne_type"),
                "confidence": classification_results.get("confidence"),
                "recommendations": classification_results.get("recommendations"),
                "classified_at": datetime.now()
            }

            result = db.sessions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "classification_results": results_data,
                    "updated_at": datetime.now()
                }}
            )

            if result.matched_count == 0:
                return False, "Session not found"

            if result.modified_count == 1:
                return True, "Classification results updated successfully"
            return True, "Classification already up-to-date"

        except Exception as e:
            print(f"❌ DB Error in update_classification_results: {str(e)}")
            return False, f"Internal server error: {str(e)}"

    @staticmethod
    def get_image_url_by_session_id(session_id):
        """
        Get the first image URL from a session

        Args:
            session_id (str): The session ID

        Returns:
            str or None: The image URL or None if not found
        """
        try:
            session = db.sessions.find_one(
                {"session_id": session_id},
                {"_id": 0, "images": 1}
            )

            if not session or not session.get("images"):
                return None

            first_image = session["images"][0]

            # Handle nested list case
            if isinstance(first_image, list):
                first_image = first_image[0] if first_image else None

            if isinstance(first_image, dict) and "url" in first_image:
                return first_image["url"]

            # Fallback if image was just a string
            if isinstance(first_image, str):
                return first_image

            return None
        except Exception as e:
            print(f"❌ DB Error in get_image_url_by_session_id: {str(e)}")
            return None
