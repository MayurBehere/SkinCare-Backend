from flask import Blueprint, request, jsonify
from models.session_model import Session
from routes.auth_routes import login_required  # Import the login_required decorator
from flask_cors import cross_origin
import traceback
import uuid
from config.database import db
from ml_model.classifier import classify_and_recommend 
import requests
from PIL import Image
from io import BytesIO
import os
from utils.api_response import success_response, error_response  # Import new utility functions

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

sessions_collection = db.sessions

session_bp = Blueprint('session', __name__)

@session_bp.route('/start-session', methods=['POST'])
@login_required  # Add login_required to protect this route
def start_session():
    try:
        data = request.json
        # Get uid from session instead of request for security
        uid = request.json.get("uid")  # Can still accept for compatibility
        
        # Validate session user matches authenticated user
        if 'uid' in request.json and request.json["uid"] != session.get("uid"):
            return error_response("Unauthorized access", status_code=403)
            
        # If no uid in request, use the one from session
        if not uid:
            uid = session.get("uid")
            
        session_name = data.get("session_name")

        print(f"Received request: uid={uid}, session_name={session_name}")

        if not uid or not session_name:
            return error_response("UID and session name are required", status_code=400)

        session_id = str(uuid.uuid4())
        Session.create_session(uid, session_id, session_name)

        return success_response("Session created successfully", 
                               {"session_id": session_id, "session_name": session_name}, 
                               status_code=201)

    except Exception as e:
        print(f"Error in start_session: {str(e)}")
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to start session", e, 500)

@session_bp.route('/get-sessions', methods=['GET', 'POST'])
@login_required  # Add login_required to protect this route
def get_sessions():
    try:
        # Get uid from session instead of request for security
        uid = session.get("uid")

        sessions = Session.get_user_sessions(uid)

        if os.environ.get("FLASK_ENV") == "development":
            print(f"Sending sessions to frontend: {sessions}")

        return success_response("Sessions retrieved successfully", {"sessions": sessions})

    except Exception as e:
        print(f"Error in get_sessions: {str(e)}")
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to get sessions", e, 500)
    
@session_bp.route("/<session_id>", methods=["GET"])
@login_required  # Add login_required to protect this route
def fetch_session_details(session_id):
    try:
        session_data = Session.get_session_by_id(session_id)
        
        # Check if the session belongs to the current user
        if not session_data or session_data.get("uid") != session.get("uid"):
            return error_response("Session not found or access denied", status_code=404)
            
        if session_data:
            return success_response("Session retrieved successfully", {
                "session_name": session_data.get("session_name"),
                "image_url": session_data.get("images", [{}])[0].get("url") if session_data.get("images") else None,
                "classification_results": session_data.get("classification_results")
            })
        else:
            return error_response("Session not found", status_code=404)
    except Exception as e:
        print(f"Error fetching session: {e}")
        return error_response("Failed to fetch session", e, 500)
    

@session_bp.route("/delete-session/<session_id>", methods=["DELETE"])
@login_required  # Add login_required to protect this route
def delete_session(session_id):
    try:
        # First verify the session belongs to the current user
        session_data = Session.get_session_by_id(session_id)
        if not session_data or session_data.get("uid") != session.get("uid"):
            return error_response("Session not found or access denied", status_code=404)
            
        success, message = Session.delete_session(session_id)

        if success:
            return success_response(message)
        else:
            return error_response(message, status_code=404)

    except Exception as e:
        print(f"Error in delete_session: {str(e)}")
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to delete session", e, 500)

@session_bp.route("/<session_id>/upload-image", methods=["POST", "OPTIONS"])
@login_required  # Add login_required to protect this route
def upload_images(session_id):
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        if os.environ.get("FLASK_ENV") == "development":
            print("Received upload request data:", data)

        # Get uid from session for security
        uid = session.get("uid")
        image_objects = data.get("image_urls")

        # First verify the session belongs to the current user
        session_data = Session.get_session_by_id(session_id)
        if not session_data or session_data.get("uid") != uid:
            return error_response("Session not found or access denied", status_code=404)

        if not image_objects:
            return error_response("Missing image URLs", status_code=400)

        if not isinstance(image_objects, list) or len(image_objects) != 1:
            return error_response("Only one image allowed per session", status_code=400)

        image_object = image_objects[0]

        if not isinstance(image_object, dict) or "url" not in image_object or "delete_url" not in image_object:
            return error_response("Invalid image object format. Must be a dict with 'url' and 'delete_url'.", status_code=400)

        # 🔄 Upload image to DB
        success, message = Session.add_images_to_session(uid, session_id, image_object)
        if not success:
            return error_response(message, status_code=500)

        # 🧠 CLASSIFY + RECOMMEND
        image_url = image_object["url"]
        print(f"[🌐] Downloading image from {image_url}")

        response = requests.get(image_url)
        if response.status_code != 200:
            return error_response("Failed to download image", status_code=500)

        if len(response.content) > 15 * 1024 * 1024:
            return error_response("Image exceeds 15MB limit", status_code=400)

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
            return error_response("Model failed to classify the image", model_error, 500)
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        # 🔄 Save classification + recommendation
        success, message = Session.update_classification_results(session_id, result)

        if not success:
            return error_response(message, status_code=500)

        return success_response("Image uploaded and classified successfully", {"result": result})

    except Exception as e:
        print("Error in upload_images:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to upload image", e, 500)

@session_bp.route("/<session_id>/classify", methods=["POST"])
@login_required  # Add login_required to protect this route
def classify_uploaded_image(session_id):
    try:
        # Verify session belongs to current user
        uid = session.get("uid")
        session_data = Session.get_session_by_id(session_id)
        if not session_data or session_data.get("uid") != uid:
            return error_response("Session not found or access denied", status_code=404)
            
        if not session_data or "images" not in session_data or not session_data["images"]:
            return error_response("No image found in session", status_code=404)

        image_url = session_data["images"][0]["url"]
        print(f"[🌐] Downloading image from {image_url}")

        response = requests.get(image_url)
        if response.status_code != 200:
            return error_response("Failed to download image", status_code=500)

        if len(response.content) > 15 * 1024 * 1024:
            return error_response("Image exceeds 15MB limit", status_code=400)

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
            return error_response("Model failed to classify the image", model_error, 500)
        finally:
            os.remove(temp_path)
            print(f"[🧹] Temp file deleted")

        # 🔄 Update in MongoDB
        success, message = Session.update_classification_results(session_id, result)

        if success:
            return success_response("Classification completed", {"result": result})
        else:
            return error_response(message, status_code=500)

    except Exception as e:
        print("Error in classify_uploaded_image:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to classify image", e, 500)

@session_bp.route("/<session_id>/update-classification", methods=["POST"])
@login_required  # Add login_required to protect this route
def update_classification(session_id):
    try:
        # Verify session belongs to current user
        uid = session.get("uid")
        session_data = Session.get_session_by_id(session_id)
        if not session_data or session_data.get("uid") != uid:
            return error_response("Session not found or access denied", status_code=404)
        
        data = request.get_json()

        if not data:
            print(f"[❌] No data received for session {session_id}")
            return error_response("No data received", status_code=400)

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
            return success_response(message)
        else:
            print(f"[⚠️] Classification update failed: {message}")
            return error_response(message, status_code=404)

    except Exception as e:
        print("Error in update_classification:", str(e))
        if os.environ.get("FLASK_ENV") == "development":
            print(traceback.format_exc())
        return error_response("Failed to update classification", e, 500)