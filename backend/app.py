from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(auth_bp)

@app.route("/", methods=["GET"])
def home():
    return {"message": "Flask Server Running!"}

if __name__ == "__main__":
    app.run(debug=True)
