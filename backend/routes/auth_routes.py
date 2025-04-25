from flask import Blueprint, request, jsonify, session
from models.user_model import User
from utils.encryption import hash_password, check_password, generate_uid
from functools import wraps
import traceback
import os

auth_bp = Blueprint('auth', __name__)

# Authentication middleware
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        existing_user = User.find_by_email(email)
        if existing_user:
            return jsonify({"error": "Email already registered"}), 409

        uid = generate_uid()
        hashed_password = hash_password(password)  # Fixed: was incorrectly calling hashed_password instead of hash_password
        User.create_user(uid, name, email, hashed_password)

        return jsonify({"message": "User registered successfully", "uid": uid}), 201

    except Exception as e:
        print("🔥 Registration error:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user = User.find_by_email(email)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
            
        # Fixed: check against hashed_password field instead of password
        if not check_password(password, user.get("hashed_password", "")):
            return jsonify({"error": "Invalid credentials"}), 401

        session['uid'] = user['uid']
        session['name'] = user['name']
        session.permanent = True

        return jsonify({"message": "Login successful"}), 200

    except Exception as e:
        print("🔥 Login error:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route('/session-info', methods=['GET'])
def session_info():
    if 'uid' not in session:
        return jsonify({'loggedIn': False}), 200  # Changed to 200 status as this is not an error
    return jsonify({
        'loggedIn': True,
        'uid': session['uid'],
        'name': session['name']
    }), 200


@auth_bp.route('/check-user-info', methods=['POST'])
@login_required  # Added login_required decorator
def check_user_info():
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
        print("🔥 Error:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            traceback.print_exc()
        return jsonify({'error': "Internal server error"}), 500


@auth_bp.route('/update-name', methods=['POST'])
@login_required  # Added login_required decorator
def update_name():
    try:
        data = request.get_json()
        uid = data.get('uid')
        name = data.get('name')

        if not uid or not name:
            return jsonify({'error': 'UID and Name are required'}), 400

        # Added: Check if the UID in the request matches the session UID for security
        if uid != session.get('uid'):
            return jsonify({'error': 'Unauthorized access'}), 403

        user = User.find_by_uid(uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        User.update_name(uid, name)
        # Update the name in the session as well
        session['name'] = name
        return jsonify({'message': 'User name updated successfully'}), 200

    except Exception as e:
        print("🔥 Error:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            traceback.print_exc()
        return jsonify({'error': 'Internal Server Error'}), 500