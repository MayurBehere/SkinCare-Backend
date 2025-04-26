import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv

load_dotenv()

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")

def init_firebase():
    if not firebase_admin._apps:  # Prevent duplicate initialization
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully!")
