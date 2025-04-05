from flask import Blueprint, request, jsonify
from models.session_model import Session
from flask_cors import cross_origin
import traceback
import uuid
from config.database import db

session_bp = Blueprint('session', __name__)

@session_bp.route('/start-session', methods=['POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def start_session():
    try:
        data = request.json
        uid = data.get("uid")
        session_name = data.get("session_name")

        print(f"Received request: uid={uid}, session_name={session_name}")

        if not uid or not session_name:
            return jsonify({"error": "UID and session name are required"}), 400

        session_id = str(uuid.uuid4())
        Session.create_session(uid, session_id, session_name)

        return jsonify({"session_id": session_id, "session_name": session_name}), 201

    except Exception as e:
        print(f"Error in start_session: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@session_bp.route('/get-sessions', methods=['GET', 'POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def get_sessions():
    try:
        uid = request.json.get("uid") if request.method == 'POST' else request.args.get("uid")

        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        sessions = Session.get_user_sessions(uid)

        print(f"Sending sessions to frontend: {sessions}")

        return jsonify({'sessions': sessions}), 200

    except Exception as e:
        print(f"Error in get_sessions: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@session_bp.route("/delete-session/<session_id>", methods=["DELETE"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def delete_session(session_id):
    try:
        success, message = Session.delete_session(session_id)

        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 404

    except Exception as e:
        print(f"Error in delete_session: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/upload-image", methods=["POST", "OPTIONS"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def upload_images(session_id):
    # For OPTIONS requests, just return headers
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        print("Received upload request data:", data)

        uid = data.get("uid")
        image_urls = data.get("image_urls")

        if not uid or not image_urls:
            return jsonify({"error": "Missing uid or image URLs"}), 400

        # Call the method with fixed field name
        success, message = Session.add_images_to_session(uid, session_id, image_urls)

        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        print("Error in upload_images:", str(e))
        print(traceback.format_exc())  # Add full traceback for debugging
        return jsonify({"error": str(e)}), 500
    
    