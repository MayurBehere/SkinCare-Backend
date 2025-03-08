import firebase_admin
from firebase_admin import auth, credentials
from flask import jsonify
from config.database import users_collection
import traceback

# Initialize Firebase
cred = credentials.Certificate("backend/config/firebase_credentials.json")
firebase_admin.initialize_app(cred)

def register_user(email, password, name):
    try:
        # Create user in Firebase Auth
        user = auth.create_user(email=email, password=password)
        uid = user.uid
        
        # Store user in MongoDB
        user_data = {"uid": uid, "email": email, "name": name}
        users_collection.insert_one(user_data)
        
        return jsonify({"message": "User registered successfully", "uid": uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def google_login(id_token):
    try:
        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', 'Unknown')
        
        # Check if user exists in MongoDB
        existing_user = users_collection.find_one({"uid": uid})
        if not existing_user:
            users_collection.insert_one({"uid": uid, "email": email, "name": name})
        
        return jsonify({"message": "Login successful", "uid": uid}), 200
    except firebase_admin.auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid ID token"}), 401
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 401

def login_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        if user:
            return jsonify({"message": "Login successful", "uid": user.uid}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
