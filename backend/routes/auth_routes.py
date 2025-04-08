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
        data = request.get_json()

        id_token = data.get('idToken') or data.get('token')
        if not id_token:
            return jsonify({'error': 'Token is required'}), 400

        # Verify Firebase ID Token
        try:
            decoded_token = auth.verify_id_token(id_token)
        except auth.InvalidIdTokenError:
            return jsonify({'error': 'Invalid Firebase ID token'}), 401
        except auth.ExpiredIdTokenError:
            return jsonify({'error': 'Firebase ID token has expired'}), 401
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': 'Token verification failed', 'details': str(e)}), 401

        # Extract user details
        uid = decoded_token.get('uid')
        email = decoded_token.get('email', None)
        name = decoded_token.get('name', 'Unknown')

        if not uid:
            return jsonify({'error': 'Token verification failed: UID missing'}), 401

        # Check user in MongoDB
        user = User.find_by_uid(uid)
        if not user:
            User.create_user(uid=uid, name=name, email=email)

        return jsonify({'message': 'User authenticated successfully', 'uid': uid}), 200

    except Exception as e:
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
        data = request.get_json()

        uid = data.get('uid')
        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        user = User.find_by_uid(uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        requires_update = user.get("name", "Unknown") == "Unknown"

        return jsonify({'requiresUpdate': requires_update, 'name': user.get("name", "Unknown")}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/update-name', methods=['POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def update_name():
    try:
        data = request.get_json()

        uid = data.get('uid')
        name = data.get('name')

        if not uid or not name:
            return jsonify({'error': 'UID and Name are required'}), 400

        user = User.find_by_uid(uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        User.update_name(uid, name)
        return jsonify({'message': 'User name updated successfully'}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error', 'details': str(e)}), 500
