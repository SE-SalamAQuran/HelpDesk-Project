from flask import Blueprint, jsonify
from app.config import get_db_connection

tickets_bp = Blueprint("tickets", __name__)


@tickets_bp.route("/tickets", methods=["GET"])
def get_tickets():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM TICKET")
        tickets = cursor.fetchall()

        return jsonify(tickets), 200

    except Exception as error:
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()