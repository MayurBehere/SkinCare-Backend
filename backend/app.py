from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp  
# from config.database import init_db
from config.firebase_config import init_firebase
import os
app = Flask(__name__)
CORS(app)

# Prevent duplicate initialization caused by Flask reloader
if not os.environ.get("FLASK_RUN_FROM_CLI"):
    init_firebase()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)  # ❌ Disable reloader
    
# Register Blueprints
app.register_blueprint(auth_bp)  

@app.route("/", methods=["GET"])
def home():
    return {"message": "Flask Server Running!"}

if __name__ == "__main__":
    app.run(debug=True)
