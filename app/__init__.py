import os
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

firebase_key = os.path.join(
    BASE_DIR,
    "Resources",
    "serviceAccountKey.json"
)

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key)
    firebase_admin.initialize_app(cred)

db = firestore.client()