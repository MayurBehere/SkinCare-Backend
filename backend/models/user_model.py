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
