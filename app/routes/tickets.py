from flask import Blueprint, jsonify, request
from app.config import get_db_connection

tickets_bp = Blueprint("tickets", __name__)


# =====================================================
# GET ALL TICKETS
# =====================================================

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
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================================
# FILTER TICKETS
# =====================================================

@tickets_bp.route("/tickets/filter", methods=["GET"])
def filter_tickets():
    connection = None
    cursor = None

    try:
        status = request.args.get("status")
        priority = request.args.get("priority")
        category = request.args.get("category")

        query = "SELECT * FROM TICKET WHERE 1=1"
        values = []

        if status:
            query += " AND Status = %s"
            values.append(status)

        if priority:
            query += " AND Priority = %s"
            values.append(priority)

        if category:
            query += " AND Category = %s"
            values.append(category)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, values)
        tickets = cursor.fetchall()

        return jsonify(tickets), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================================
# SEARCH TICKETS
# =====================================================

@tickets_bp.route("/tickets/search", methods=["GET"])
def search_tickets():
    connection = None
    cursor = None

    try:
        search = request.args.get("q")

        if not search:
            return jsonify({
                "message": "Please enter a search value"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT * FROM TICKET
            WHERE Title LIKE %s
            OR Description LIKE %s
        """

        search_value = f"%{search}%"

        cursor.execute(
            query,
            (search_value, search_value)
        )

        tickets = cursor.fetchall()

        return jsonify(tickets), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================================
# GET TICKET BY ID
# =====================================================

@tickets_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket_by_id(ticket_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        ticket = cursor.fetchone()

        if ticket is None:
            return jsonify({
                "message": "Ticket not found"
            }), 404

        return jsonify(ticket), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()