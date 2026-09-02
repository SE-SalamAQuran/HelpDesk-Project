import os
import firebase_admin

from flask import Flask
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


def create_app():
    app = Flask(__name__)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.attachment import attachment_bp
    app.register_blueprint(attachment_bp)

    from app.routes.frontend import frontend_bp
    app.register_blueprint(frontend_bp)

    return app