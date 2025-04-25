from config.database import init_db
import os

db = init_db()

class User:
    collection = db["users"]

    @staticmethod
    def create_user(uid, name, email, hashed_password):
        user_data = {
            "uid": uid,
            "name": name,
            "email": email,
            "hashed_password": hashed_password  # Consistent field name
        }
        User.collection.insert_one(user_data)

    @staticmethod
    def find_by_email(email):
        return User.collection.find_one({"email": email})

    @staticmethod
    def find_by_uid(uid):
        return User.collection.find_one({"uid": uid})

    @staticmethod
    def update_name(uid, name):
        try:
            if os.environ.get("FLASK_ENV") == "development":
                print(f"📌 Attempting to update name - UID: {uid}, New Name: {name}")

            result = User.collection.update_one({"uid": uid}, {"$set": {"name": name}})

            if os.environ.get("FLASK_ENV") == "development":
                print(f"✅ MongoDB Update Result: Acknowledged: {result.acknowledged}, "
                      f"Matched: {result.matched_count}, Modified: {result.modified_count}")

            if result.matched_count == 0:
                raise Exception("User not found")

            return result

        except Exception as e:
            print(f"🔥 Error in update_name: {str(e)}")
            raise