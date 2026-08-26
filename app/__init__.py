from flask import Flask
from app.routes.tickets import tickets_bp


def create_app():
    app = Flask(__name__)

    app.register_blueprint(tickets_bp)

    return app