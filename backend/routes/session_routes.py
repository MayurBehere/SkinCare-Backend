from flask import Blueprint, request, jsonify
from models.session_model import Session
from flask_cors import cross_origin
import traceback
import uuid
from config.database import db
from ml_model.classifier import classify_and_recommend 
import requests
from PIL import Image
from io import BytesIO
import os

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

sessions_collection = db.sessions

session_bp = Blueprint('session', __name__)

@session_bp.route('/start-session', methods=['POST'])
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
    
@session_bp.route("/<session_id>", methods=["GET"])
def fetch_session_details(session_id):
    try:
        session = Session.get_session_by_id(session_id)
        if session:
            return jsonify({
                "session_name": session.get("session_name"),
                "image_url": session.get("images", [{}])[0].get("url") if session.get("images") else None,
                "classification_results": session.get("classification_results")
            }), 200
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        print(f"Error fetching session: {e}")
        return jsonify({"error": "Failed to fetch session"}), 500
    

@session_bp.route("/delete-session/<session_id>", methods=["DELETE"])
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

        if not isinstance(image_objects, list) or len(image_objects) != 1:
            return jsonify({"error": "Only one image allowed per session."}), 400

        image_object = image_objects[0]

        if not isinstance(image_object, dict) or "url" not in image_object or "delete_url" not in image_object:
            return jsonify({"error": "Invalid image object format. Must be a dict with 'url' and 'delete_url'."}), 400

        # 🔄 Upload image to DB
        success, message = Session.add_images_to_session(uid, session_id, image_object)
        if not success:
            return jsonify({"error": message}), 500

        # 🧠 CLASSIFY + RECOMMEND
        image_url = image_object["url"]
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
            print(f"[🧠] Running classification and recommendation for session {session_id}")
            result = classify_and_recommend(image_url)  # ✅ UPDATED FUNCTION
            print(f"[✅] Classification + Recommendation result:\n{result}")
        except Exception as model_error:
            print(f"[❌] Error in model prediction: {model_error}")
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        # 🔄 Save classification + recommendation
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
            print(f"[🧠] Running classification and recommendation for session {session_id}")
            result = classify_and_recommend(temp_path)  # ✅ UPDATED FUNCTION
            print(f"[✅] Classification + Recommendation result:\n{result}")
        except Exception as model_error:
            print(f"[❌] Error in model prediction: {model_error}")
            return jsonify({"error": "Model failed to classify the image."}), 500
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        # 🔄 Update in MongoDB
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
def update_classification(session_id):
    try:
        data = request.get_json()

        if not data:
            print(f"[❌] No data received for session {session_id}")
            return jsonify({"error": "No data received"}), 400

        classification = data.get("classification")
        recommendations = data.get("recommendations")

        print(f"[📩] Received classification update for session {session_id}")
        print(f"   🧾 Classification: {classification}")
        print(f"   💡 Recommendations: {recommendations}")

        result_data = {
            "classification": classification,
            "recommendations": recommendations
        }

        success, message = Session.update_classification_results(session_id, result_data)

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