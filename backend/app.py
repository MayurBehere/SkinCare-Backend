from dotenv import load_dotenv
import os
load_dotenv()  
from flask import Flask
from flask_session import Session
from flask_cors import CORS
from routes.auth_routes import auth_bp  
from routes.session_routes import session_bp
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

# 🔐 Secret key for session cookies
app.secret_key = os.environ.get("SECRET_KEY")

# Session configuration
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"  # True in production
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(days=7)

# 🔁 Enable server-side sessions
Session(app)

# CSRF protection
csrf = CSRFProtect(app)
# Exempt the auth routes from CSRF protection for API use
csrf.exempt(auth_bp)

# ✅ Apply CORS with credentials
CORS(app,
     origins=["http://localhost:5173"],  # Changed to list for multiple origins
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],  # Added CSRF token header
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],  # Added CSRF token header
     max_age=timedelta(hours=1))

# Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')  
app.register_blueprint(session_bp, url_prefix='/session')

@app.route("/", methods=["GET"])
def home():
    return {"message": "Flask Server Running!"}

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)