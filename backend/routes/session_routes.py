from flask import Blueprint, request, jsonify
from models.session_model import Session
from flask_cors import cross_origin
import traceback
import uuid
from config.database import db
from ml_model.classifier import classify_image
import os
import requests
from PIL import Image
from io import BytesIO

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

sessions_collection = db.sessions

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

@session_bp.route('/get-sessions', methods=['GET'])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def get_sessions_by_uid():
    try:
        uid = request.args.get("uid")
        if not uid:
            return jsonify({"error": "UID is required"}), 400

        sessions = Session.get_user_sessions(uid)
        if not sessions:
            return jsonify({"sessions": []}), 200  

        return jsonify({"sessions": sessions}), 200

    except Exception as e:
        print("Error in get_sessions_by_uid:", str(e))
        print(traceback.format_exc())
        return jsonify({"error": "Failed to fetch sessions"}), 500

# Now the generic session_id route comes AFTER the specific routes
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
        print(f"Error fetching session: {e}")
        return jsonify({"error": "Failed to fetch session"}), 500

# Removed the duplicate try/except block in fetch_session_details

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
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        print("Received upload request data:", data)

        uid = data.get("uid")
        image_objects = data.get("image_urls")

        if not uid or not image_objects:
            return jsonify({"error": "Missing uid or image URLs"}), 400

        if len(image_objects) > 1:
            return jsonify({"error": "Only one image allowed per session."}), 400

        for img in image_objects:
            if not isinstance(img, dict) or "url" not in img or "delete_url" not in img:
                return jsonify({"error": "Invalid image object format."}), 400

        # 🔄 Upload image
        success, message = Session.add_images_to_session(uid, session_id, image_objects[0])
        if not success:
            return jsonify({"error": message}), 500

        # 🧠 CLASSIFY AUTOMATICALLY
        image_url = image_objects[0]["url"]
        print(f"[🌐] Downloading image from {image_url}")

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
        print(f"[💾] Saved temporary image to {temp_path}")

        try:
            print(f"[🧠] Classifying image for session {session_id}")
            result = classify_image(temp_path)
            print(f"[✅] Classification result: {result}")
        except Exception as model_error:
            print(f"[❌] Error in model prediction: {model_error}")
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        # 🔄 Save result
        success, message = Session.update_classification_results(session_id, result)

        if not success:
            return jsonify({"error": message}), 500

        return jsonify({
            "message": "Image uploaded and classified successfully",
            "result": result
        }), 200

    except Exception as e:
        print("Error in upload_images:", str(e))
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/classify", methods=["POST"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def classify_uploaded_image(session_id):
    try:
        session_data = Session.get_session_by_id(session_id)
        if not session_data or "images" not in session_data or not session_data["images"]:
            return jsonify({"error": "No image found in session"}), 404

        image_url = session_data["images"][0]["url"]
        print(f"[🌐] Downloading image from {image_url}")

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
        print(f"[💾] Saved temporary image to {temp_path}")

        try:
            print(f"[🧠] Classifying image for session {session_id}")
            result = classify_image(temp_path)
            print(f"[✅] Classification result: {result}")
        except Exception as model_error:
            print(f"[❌] Error in model prediction: {model_error}")
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        success, message = Session.update_classification_results(session_id, result)

        if success:
            return jsonify({"result": result}), 200
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        print("Error in classify_uploaded_image:", str(e))
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@session_bp.route("/<session_id>/update-classification", methods=["POST"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True)
def update_classification(session_id):
    try:
        data = request.get_json()

        if not data:
            print(f"[❌] No data received for session {session_id}")
            return jsonify({"error": "No data received"}), 400

        print(f"Received classification update for session {session_id}: {data}")

        success, message = Session.update_classification_results(session_id, data)

        if success:
            print(f"[✅] Classification update successful for session {session_id}")
            return jsonify({"message": message}), 200
        else:
            print(f"[⚠️] Classification update failed: {message}")
            return jsonify({"error": message}), 404

    except Exception as e:
        print("Error in update_classification:", str(e))
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500