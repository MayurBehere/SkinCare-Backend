import firebase_admin
from firebase_admin import auth, credentials
from flask import request, jsonify
from config.database import users_collection
import traceback

# Initialize Firebase
cred = credentials.Certificate("config/firebase_credentials.json")
firebase_admin.initialize_app(cred)
 
def verify_firebase_token():
    """
    Verifies the Firebase ID token sent from the frontend.
    If the user does not exist in MongoDB, it creates a new entry.
    """
    try:
        # Get token from request
        data = request.json
        firebase_token = data.get("token")

        if not firebase_token:
            return jsonify({"error": "Token is required"}), 400

        # Verify Firebase token
        decoded_token = auth.verify_id_token(firebase_token)
        uid = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "Unknown")

        # Check if user exists in MongoDB
        existing_user = users_collection.find_one({"uid": uid})
        if not existing_user:
            user_data = {"uid": uid, "email": email, "name": name}
            users_collection.insert_one(user_data)

        return jsonify({"message": "User verified successfully", "uid": uid}), 200

    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 400


def update_name_logic(uid, name):
    """
    Updates the name of a user in MongoDB.
    """
    user = User.find_by_uid(uid)
    if not user:
        return {"error": "User not found"}, 404

    User.update_name(uid, name)
    return {"message": "Name updated successfully"}, 200