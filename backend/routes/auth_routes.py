from flask import Blueprint, request, jsonify
from firebase_admin import auth
from models.user_model import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    data = request.get_json()
    id_token = data.get('idToken')

    try:
        # Verify Firebase ID Token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name')

        # Check if user exists in MongoDB
        user = User.find_by_uid(uid)
        if not user:
            # Store user in MongoDB if new
            User.create_user(uid=uid, name=name, email=email)

        return jsonify({'message': 'User authenticated', 'uid': uid}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401
