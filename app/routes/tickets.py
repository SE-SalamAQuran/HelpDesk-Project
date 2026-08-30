from flask import Blueprint, jsonify, request
from app.config import get_db_connection

tickets_bp = Blueprint("tickets", __name__)


# =====================================================
# GET ALL TICKETS + FILTERS + PAGINATION
# =====================================================

@tickets_bp.route("/tickets", methods=["GET"])
def get_tickets():
    connection = None
    cursor = None

    try:
        category = request.args.get("category")
        status = request.args.get("status")
        created_by = request.args.get("created_by")
        created_at = request.args.get("created_at")
        priority = request.args.get("priority")

        page = request.args.get("page", default=1, type=int) or 1
        per_page = request.args.get("per_page", default=5, type=int) or 5

        if page < 1:
            page = 1

        if per_page < 1:
            per_page = 5

        if per_page > 100:
            per_page = 100

        query = " FROM TICKET WHERE 1=1"
        values = []

        if category:
            query += " AND Category = %s"
            values.append(category)

        if status:
            query += " AND Status = %s"
            values.append(status)

        if created_by:
            query += " AND Created_By = %s"
            values.append(created_by)

        if created_at:
            query += " AND DATE(Created_At) = %s"
            values.append(created_at)

        if priority:
            query += " AND Priority = %s"
            values.append(priority)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        count_query = "SELECT COUNT(*) AS total" + query

        cursor.execute(count_query, values)
        total = cursor.fetchone()["total"]

        offset = (page - 1) * per_page

        tickets_query = (
            "SELECT *"
            + query
            + " ORDER BY ID ASC LIMIT %s OFFSET %s"
        )

        ticket_values = values + [per_page, offset]

        cursor.execute(tickets_query, ticket_values)
        tickets = cursor.fetchall()

        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            "page": page,
            "per_page": per_page,
            "total_tickets": total,
            "total_pages": total_pages,
            "tickets": tickets
        }), 200

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
# CREATE NEW TICKET
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
        priority = data.get("priority", "Medium")

        if not title or not created_by:
            return jsonify({
                "message": "title and created_by are required"
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
# SEARCH TICKETS
# Search by: title, description, created_by
# Supports multiple field search
# =====================================================

@tickets_bp.route("/tickets/search", methods=["GET"])
def search_tickets():
    connection = None
    cursor = None

    try:
        title = request.args.get("title")
        description = request.args.get("description")
        created_by = request.args.get("created_by")

        if not title and not description and not created_by:
            return jsonify({
                "message": "Enter title, description, or created_by"
            }), 400

        query = "SELECT * FROM TICKET WHERE 1=1"
        values = []

        if title:
            query += " AND Title LIKE %s"
            values.append(f"%{title}%")

        if description:
            query += " AND Description LIKE %s"
            values.append(f"%{description}%")

        if created_by:
            query += " AND Created_By = %s"
            values.append(created_by)

        query += " ORDER BY ID ASC"

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

        title = data.get("title", ticket["Title"])

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