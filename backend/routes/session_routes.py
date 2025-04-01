from flask import Blueprint, request, jsonify
from models.session_model import Session
import cloudinary.uploader
from flask_cors import cross_origin
import traceback

session_bp = Blueprint('session', __name__)

@session_bp.route('/start-session', methods=['POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def start_session():
    """
    Creates a new session for the user and returns the session ID.
    """
    try:
        data = request.get_json()
        uid = data.get('uid')

        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        session_id = Session.create_new_session(uid)
        return jsonify({'message': 'New session created', 'session_id': session_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/upload-image', methods=['POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def upload_image():
    """
    Uploads an image to Cloudinary and stores the URL in MongoDB under the session.
    """
    try:
        uid = request.form.get('uid')
        session_id = request.form.get('session_id')

        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        image_file = request.files['image']

        # Upload image to Cloudinary
        upload_result = cloudinary.uploader.upload(image_file)
        image_url = upload_result['secure_url']

        # Save image URL in MongoDB
        Session.store_image(uid, session_id, image_url)

        return jsonify({'message': 'Image uploaded successfully', 'image_url': image_url}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/get-sessions', methods=['GET', 'POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def get_sessions():
    """
    Retrieves all previous sessions of a user.
    """
    try:
        # Handle both GET and POST methods
        if request.method == 'POST':
            data = request.get_json()
            uid = data.get('uid')
        else:  # GET
            uid = request.args.get('uid')

        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        sessions = Session.get_user_sessions(uid)
        return jsonify({'sessions': sessions}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route("/delete/<session_id>", methods=["DELETE"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def delete_session(session_id):
    """
    Deletes a session and all associated images from MongoDB.
    """
    try:
        # Call the delete logic
        success, message = Session.delete_session(session_id)

        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 404

    except Exception as e:
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e),
            "traceback": traceback.format_exc()
        }), 500