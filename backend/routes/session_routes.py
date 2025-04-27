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
from math import radians, sin, cos, sqrt, asin

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

@session_bp.route("/<session_id>/nearest-dermatologists", methods=["GET"])
def get_nearest_dermatologists(session_id):
    USE_MOCK_DATA = False  # Set to True if you want mock data during testing

    def haversine_distance(lat1, lon1, lat2, lon2):
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of Earth in kilometers
        return c * r

    if USE_MOCK_DATA:
        print("[🔧] Using mock dermatologist data")
        mock_data = [
            {
                "name": "Dr. Sarah Johnson",
                "vicinity": "123 Health Avenue, Pune",
                "rating": 4.8,
                "user_ratings_total": 124,
                "place_id": "mock-place-1",
                "distance_km": 2.5
            },
            {
                "name": "Dermatology Specialists",
                "vicinity": "456 Medical Plaza, Pune",
                "rating": 4.5,
                "user_ratings_total": 89,
                "place_id": "mock-place-2",
                "distance_km": 4.1
            },
        ]
        return jsonify({"dermatologists": mock_data}), 200

    try:
        print(f"[📥] Received request for dermatologists near session {session_id}")

        # 1. Fetch session (optional if needed)
        session_data = Session.get_session_by_id(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404

        # 2. Get coordinates from query params
        lat = request.args.get("lat")
        lng = request.args.get("lng")

        if not lat or not lng:
            return jsonify({"error": "Must provide lat & lng parameters"}), 400

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return jsonify({"error": "Invalid lat/lng format"}), 400

        # 3. Google Places API setup
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            return jsonify({"error": "Google Places API key not configured"}), 500

        api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": request.args.get("radius", default=10000, type=int),
            "type": "doctor",
            "keyword": "dermatologist",
            "key": api_key
        }

        # 4. Call Google API
        response = requests.get(api_url, params=params)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch from Google Places API"}), 502

        data = response.json()
        if data.get("status") != "OK":
            return jsonify({"error": f"Google Places API error: {data.get('error_message', 'Unknown error')}"}), 502

        # 5. Parse and calculate distance
        dermatologists = []
        for place in data.get("results", []):
            # extract coords
            lat2 = place.get("geometry", {}).get("location", {}).get("lat")
            lng2 = place.get("geometry", {}).get("location", {}).get("lng")
            if lat2 is None or lng2 is None:
                continue

            dist = haversine_distance(lat, lng, lat2, lng2)

            # filter: within 10 km AND at least 4-star
            if dist > 10 or place.get("rating", 0) < 4:
                continue

            dermatologists.append({
                "name": place.get("name", "Unknown"),
                "vicinity": place.get("vicinity", "Address not available"),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "place_id": place.get("place_id", ""),
                "distance_km": round(dist, 2)
            })

        # 6. Sort by distance & 7. Limit to 4 nearest
        dermatologists.sort(key=lambda d: d["distance_km"])
        return jsonify({"dermatologists": dermatologists[:4]}), 200

        # 7. Return top 5 nearest
        return jsonify({"dermatologists": dermatologists[:5]}), 200

    except Exception as e:
        print(f"[❌] Error in get_nearest_dermatologists: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500