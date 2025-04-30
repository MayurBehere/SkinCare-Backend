from flask import Blueprint, request, jsonify
from firebase_admin import auth
from flask_cors import cross_origin
from models.user_model import User
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Accepts UID and Email directly from frontend (NO token verification).
    WARNING: Only for local development.
    """
    try:
        print("📥 Received /verify-token request")
        data = request.get_json()
        print(f"📦 Request Data: {data}")

        uid = data.get('uid')
        email = data.get('email')
        name = data.get('name', 'Unknown')

        if not uid:
            print("❌ UID missing")
            return jsonify({'error': 'UID is required'}), 400

        if not email:
            print("⚠️ Email missing for UID: {uid}")

        print(f"👤 UID: {uid}, Email: {email}, Name: {name}")

        # Check if user exists in DB
        user = User.find_by_uid(uid)
        if not user:
            print("🆕 New user, creating in MongoDB")
            User.create_user(uid=uid, name=name, email=email)
        else:
            print("✅ User already exists in DB")

        print("✅ User authenticated and processed")
        return jsonify({'message': 'User authenticated successfully', 'uid': uid}), 200

    except Exception as e:
        print(f"🔥 Internal Server Error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': 'Internal Server Error',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500


@auth_bp.route('/check-user-info', methods=['GET', 'POST'])
def check_user_info():
    """
    Checks if the user's name is "Unknown" and requires an update.
    """
    try:
        print("📥 Received /check-user-info request")
        data = request.get_json()
        print(f"📦 Request Data: {data}")

        uid = data.get('uid')
        if not uid:
            print("❌ UID missing")
            return jsonify({'error': 'UID is required'}), 400

        user = User.find_by_uid(uid)
        if not user:
            print(f"❌ User with UID {uid} not found")
            return jsonify({'error': 'User not found'}), 404

        requires_update = user.get("name", "Unknown") == "Unknown"
        print(f"🔍 Name check result: requiresUpdate = {requires_update}, Name = {user.get('name')}")

        return jsonify({'requiresUpdate': requires_update, 'name': user.get("name", "Unknown")}), 200

    except Exception as e:
        print(f"🔥 Internal Server Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/update-name', methods=['POST'])
def update_name():
    try:
        print("📥 Received /update-name request")
        data = request.get_json()
        print(f"📦 Request Data: {data}")

        uid = data.get('uid')
        name = data.get('name')

        print(f"📌 Update request: UID={uid}, Name={name}")

        if not uid or not name:
            print("❌ Missing UID or Name")
            return jsonify({'error': 'UID and Name are required'}), 400

        user = User.find_by_uid(uid)
        if not user:
            print(f"❌ User with UID {uid} not found in DB")
            return jsonify({'error': 'User not found'}), 404

        User.update_name(uid, name)
        print("✅ User name updated successfully")
        return jsonify({'message': 'User name updated successfully'}), 200

    except Exception as e:
        print(f"🔥 Internal Server Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error', 'details': str(e)}), 500