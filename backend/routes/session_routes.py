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

        if not uid or not session_name:
            return jsonify({"error": "UID and session name are required"}), 400

        session_id = str(uuid.uuid4())
        Session.create_session(uid, session_id, session_name)

        return jsonify({"session_id": session_id, "session_name": session_name}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@session_bp.route('/get-sessions', methods=['GET', 'POST'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def get_sessions():
    try:
        uid = request.json.get("uid") if request.method == 'POST' else request.args.get("uid")

        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        sessions = Session.get_user_sessions(uid)

        return jsonify({'sessions': sessions}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@session_bp.route("/<session_id>", methods=["GET"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def fetch_session_details(session_id):
    try:
        session = Session.get_session_by_id(session_id)
        if session:
            return jsonify({
                "session_name": session.get("session_name"),
                "image_url": session.get("images", [{}])[0].get("url") if session.get("images") else None,
                "prediction": session.get("result")
            }), 200
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to fetch session"}), 500
    try:
        session = Session.get_session_by_id(session_id)
        if session:
            return jsonify(session), 200
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
<<<<<<< HEAD
        print(f"Error fetching session: {e}")
=======
>>>>>>> parent of dd29f18 (testing routes)
        return jsonify({"error": "Failed to fetch session"}), 500

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
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/upload-image", methods=["POST", "OPTIONS"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def upload_images(session_id):
    # For OPTIONS requests, just return headers
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()

        uid = data.get("uid")
        image_urls = data.get("image_urls")

        if not uid or not image_urls:
            return jsonify({"error": "Missing uid or image URLs"}), 400

        if len(image_objects) > 1:
            return jsonify({"error": "Only one image allowed per session."}), 400

        for img in image_objects:
            if not isinstance(img, dict) or "url" not in img or "delete_url" not in img:
                return jsonify({"error": "Invalid image object format."}), 400

        # 🔄 Upload image
        success, message = Session.add_images_to_session(uid, session_id, image_objects)

        if not success:
            return jsonify({"error": message}), 500

        # 🧠 CLASSIFY AUTOMATICALLY
        image_url = image_objects[0]["url"]

        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download image"}), 500

        if len(response.content) > 15 * 1024 * 1024:
            return jsonify({"error": "Image exceeds 15MB limit"}), 400

        image = Image.open(BytesIO(response.content))
        if image.mode != "RGB":
            image = image.convert("RGB")

        ext = image.format.lower() if image.format else "jpg"
        temp_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.{ext}")
        image.save(temp_path)

        try:
            result = classify_image(temp_path)
        except Exception as model_error:
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)

        # 🔄 Save result
        success, message = Session.update_classification_results(session_id, result)

        if not success:
            return jsonify({"error": message}), 500

        return jsonify({
            "message": "Image uploaded and classified successfully",
            "result": result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/classify", methods=["POST"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def classify_uploaded_image(session_id):
    try:
        session_data = Session.get_session_by_id(session_id)
        if not session_data or "images" not in session_data or not session_data["images"]:
            return jsonify({"error": "No image found in session"}), 404

        image_url = session_data["images"][0]["url"]

        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download image"}), 500

        if len(response.content) > 15 * 1024 * 1024:
            return jsonify({"error": "Image exceeds 15MB limit"}), 400

        image = Image.open(BytesIO(response.content))
        if image.mode != "RGB":
            image = image.convert("RGB")

        ext = image.format.lower() if image.format else "jpg"
        temp_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.{ext}")
        image.save(temp_path)

        try:
            result = classify_image(temp_path)
        except Exception as model_error:
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)

        success, message = Session.update_classification_results(session_id, result)

        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
<<<<<<< HEAD
        print("Error in upload_images:", str(e))
        print(traceback.format_exc())  # Add full traceback for debugging
=======
>>>>>>> parent of dd29f18 (testing routes)
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/update-classification", methods=["POST"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def update_classification(session_id):
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        success, message = Session.update_classification_results(session_id, data)

        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 404

    except Exception as e:
        print("Error in update_classification:", str(e))
        print(traceback.format_exc())
=======
>>>>>>> parent of dd29f18 (testing routes)
        return jsonify({"error": str(e)}), 500
