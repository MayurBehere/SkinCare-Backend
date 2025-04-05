from config.database import init_db

db = init_db()  
class User:
    collection = db["users"]
    
    @staticmethod
    def create_user(uid, name, email):
        user_data = {
            "uid": uid,
            "name": name,
            "email": email
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
            print(f"📌 Attempting to update name - UID: {uid}, New Name: {name}")  # Debug

            # Check if user exists before updating
            user = User.collection.find_one({"uid": uid})
            if not user:
                print(f"❌ User with UID {uid} not found in MongoDB")
                raise Exception("User not found")

            # Perform the update
            result = User.collection.update_one({"uid": uid}, {"$set": {"name": name}})

            print(f"✅ MongoDB Update Result: Acknowledged: {result.acknowledged}, Matched: {result.matched_count}, Modified: {result.modified_count}")

            if result.matched_count == 0:
                raise Exception("Update failed: No matching UID found")

            return result

        except Exception as e:
            print(f"🔥 Error in update_name: {str(e)}")  # Print exact error in console
            raise


