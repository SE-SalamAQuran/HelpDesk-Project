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
        return jsonify({
            "error": str(error)
        }), 500

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
        return jsonify({
            "error": str(error)
        }), 500

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

        search_value = f"%{search}%"

        query = """
            SELECT * FROM TICKET
            WHERE Title LIKE %s
            OR Description LIKE %s
        """

        cursor.execute(
            query,
            (search_value, search_value)
        )

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


# =====================================================
# CREATE TICKET
# =====================================================

@tickets_bp.route("/tickets", methods=["POST"])
def create_ticket():
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "message": "JSON data is required"
            }), 400

        title = data.get("title")
        description = data.get("description")
        created_by = data.get("created_by")
        assigned_to = data.get("assigned_to")
        category = data.get("category", "HR")
        status = data.get("status", "Open")
        priority = data.get("priority")

        if not title or not created_by or not priority:
            return jsonify({
                "message": "title, created_by and priority are required"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            INSERT INTO TICKET
            (
                Title,
                Description,
                Created_By,
                Assigned_To,
                Category,
                Status,
                Priority
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            title,
            description,
            created_by,
            assigned_to,
            category,
            status,
            priority
        )

        cursor.execute(query, values)
        connection.commit()

        ticket_id = cursor.lastrowid

        cursor.execute(
            "SELECT * FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        new_ticket = cursor.fetchone()

        return jsonify(new_ticket), 201

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

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
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================================
# UPDATE TICKET
# =====================================================

@tickets_bp.route("/tickets/<int:ticket_id>", methods=["PUT"])
def update_ticket(ticket_id):
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "message": "JSON data is required"
            }), 400

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

        title = data.get(
            "title",
            ticket["Title"]
        )

        description = data.get(
            "description",
            ticket["Description"]
        )

        assigned_to = data.get(
            "assigned_to",
            ticket["Assigned_To"]
        )

        category = data.get(
            "category",
            ticket["Category"]
        )

        status = data.get(
            "status",
            ticket["Status"]
        )

        priority = data.get(
            "priority",
            ticket["Priority"]
        )

        query = """
            UPDATE TICKET
            SET Title = %s,
                Description = %s,
                Assigned_To = %s,
                Category = %s,
                Status = %s,
                Priority = %s
            WHERE ID = %s
        """

        values = (
            title,
            description,
            assigned_to,
            category,
            status,
            priority,
            ticket_id
        )

        cursor.execute(query, values)
        connection.commit()

        cursor.execute(
            "SELECT * FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        updated_ticket = cursor.fetchone()

        return jsonify(updated_ticket), 200

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================================
# DELETE TICKET
# =====================================================

@tickets_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
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

        cursor.execute(
            "DELETE FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Ticket deleted successfully"
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()