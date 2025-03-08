import firebase_admin
from firebase_admin import credentials, auth
import os

# Get the absolute path of the Firebase credentials file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.path.join(BASE_DIR, "firebase_credentials.json")

# Initialize Firebase App
cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred)
