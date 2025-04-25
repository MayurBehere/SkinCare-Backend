from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp  
from routes.session_routes import session_bp
from config.firebase_config import init_firebase
import os
from datetime import timedelta

app = Flask(__name__)

# ✅ Apply CORS to the entire app
CORS(app,
     origins="http://localhost:5173",  # Make this a single string, not a list
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type", "Authorization"],
     max_age=timedelta(hours=1))  # Optional: helps with caching preflight

# Initialize Firebase
if not os.environ.get("FLASK_RUN_FROM_CLI"):
    init_firebase()

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')  
app.register_blueprint(session_bp, url_prefix='/session')

@app.route("/", methods=["GET"])
def home():
    return {"message": "Flask Server Running!"}

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)