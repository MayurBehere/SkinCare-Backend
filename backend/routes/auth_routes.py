from flask import Blueprint, request, jsonify
from firebase_admin import auth
from flask_cors import cross_origin
from models.user_model import User
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/verify-token', methods=['POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def verify_token():
    """
    Verifies Firebase ID token and creates the user in MongoDB if not already present.
    """
    try:
        print("📥 Received /verify-token request")
        data = request.get_json()
        print(f"📦 Request Data: {data}")

        id_token = data.get('idToken') or data.get('token')
        if not id_token:
            print("❌ No token found in request")
            return jsonify({'error': 'Token is required'}), 400

        # Verify Firebase ID Token
        try:
            decoded_token = auth.verify_id_token(id_token)
            print(f"🔑 Token Decoded: {decoded_token}")
        except auth.InvalidIdTokenError:
            print("❌ Invalid Firebase ID token")
            return jsonify({'error': 'Invalid Firebase ID token'}), 401
        except auth.ExpiredIdTokenError:
            print("❌ Firebase ID token has expired")
            return jsonify({'error': 'Firebase ID token has expired'}), 401
        except Exception as e:
            print(f"❌ Token verification failed: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': 'Token verification failed', 'details': str(e)}), 401

        # Extract user details
        uid = decoded_token.get('uid')
        email = decoded_token.get('email', None)
        name = decoded_token.get('name', 'Unknown')

        print(f"👤 UID: {uid}, Email: {email}, Name: {name}")

        if not uid:
            print("❌ UID missing in decoded token")
            return jsonify({'error': 'Token verification failed: UID missing'}), 401

        if not email:
            print(f"⚠️ UID {uid} has no associated email")

        # Check user in MongoDB
        user = User.find_by_uid(uid)
        if not user:
            print("🆕 New user, creating in MongoDB")
            User.create_user(uid=uid, name=name, email=email)
        else:
            print("✅ User exists in DB")

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
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
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
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
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
