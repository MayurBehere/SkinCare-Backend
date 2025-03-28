import firebase_admin
from firebase_admin import auth, credentials
from flask import jsonify
from config.database import users_collection
import traceback

# Initialize Firebase
cred = credentials.Certificate("config/firebase_credentials.json")
firebase_admin.initialize_app(cred)

def register_user(email, password, name):
    try:
        # Create user in Firebase Auth
        user = auth.create_user(email=email, password=password, display_name=name)
        uid = user.uid

        # Store user in MongoDB
        user_data = {"uid": uid, "email": email, "name": name}
        users_collection.insert_one(user_data)

        return jsonify({"message": "User registered successfully", "uid": uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400