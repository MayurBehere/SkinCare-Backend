from flask import Blueprint, request, jsonify
from controllers.auth_controller import register_user, google_login ,login_user

auth_bp = Blueprint('auth', __name__)  # Renamed from auth_routes to auth_bp

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    return register_user(data['email'], data['password'], data['name'])

@auth_bp.route('/login/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    return google_login(data['id_token'])

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    return login_user(data['email'], data['password'])
