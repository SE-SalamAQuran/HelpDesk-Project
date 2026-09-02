import mysql.connector
from flask import Blueprint, jsonify, request
from app.config import get_db_connection
from datetime import date, datetime, timedelta

tickets_bp = Blueprint("tickets", __name__)


@tickets_bp.route("/api/tickets", methods=["GET"])
def get_tickets():
    connection = None
    cursor = None

    try:
        category = request.args.get("category")
        status = request.args.get("status")
        created_by = request.args.get("created_by")
        priority = request.args.get("priority")

        from_date = request.args.get(
            "from_date",
            (date.today() - timedelta(days=90)).isoformat()
        )

        to_date = request.args.get(
            "to_date",
            date.today().isoformat()
        )

        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").date()
            end = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Date must be YYYY-MM-DD"}), 400

        if start > end:
            return jsonify({
                "error": "from_date must be before to_date"
            }), 400

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 5, type=int)

        if page < 1:
            page = 1

        if per_page < 1:
            per_page = 5

        offset = (page - 1) * per_page

        query = "SELECT * FROM TICKET WHERE 1=1"
        count_query = "SELECT COUNT(*) AS total FROM TICKET WHERE 1=1"

        conditions = ""
        values = []

        if category:
            conditions += " AND Category = %s"
            values.append(category)

        if status:
            conditions += " AND Status = %s"
            values.append(status)

        if created_by:
            conditions += " AND Created_By = %s"
            values.append(created_by)

        if priority:
            conditions += " AND Priority = %s"
            values.append(priority)

        conditions += " AND DATE(Created_At) BETWEEN %s AND %s"
        values.extend([from_date, to_date])

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(count_query + conditions, values)
        total = cursor.fetchone()["total"]

        query += conditions + " ORDER BY ID ASC LIMIT %s OFFSET %s"

        cursor.execute(
            query,
            values + [per_page, offset]
        )

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
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# CREATE
@tickets_bp.route("/tickets", methods=["POST"])
def create_ticket():
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data or not data.get("title") or not data.get("created_by"):
            return jsonify({
                "error": "title and created_by are required"
            }), 400

        query = """
            INSERT INTO TICKET
            (Title, Description, Created_By, Assigned_To,
             Category, Status, Priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            data.get("title"),
            data.get("description"),
            data.get("created_by"),
            data.get("assigned_to"),
            data.get("category", "HR"),
            data.get("status", "Open"),
            data.get("priority", "Medium")
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(query, values)
        connection.commit()

        data["ID"] = cursor.lastrowid

        return jsonify(data), 201

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# SEARCH
@tickets_bp.route("/tickets/search", methods=["GET"])
def search_tickets():
    connection = None
    cursor = None

    try:
        word = request.args.get("q")

        if not word:
            return jsonify({"error": "Search word is required"}), 400

        search = f"%{word}%"

        query = """
            SELECT t.*, u.Full_Name AS Created_By_Name
            FROM TICKET t
            LEFT JOIN `USER` u ON t.Created_By = u.ID
            WHERE t.Title LIKE %s
               OR t.Description LIKE %s
               OR u.Full_Name LIKE %s
               OR CAST(t.Created_By AS CHAR) LIKE %s
            ORDER BY t.ID ASC
        """

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, (search, search, search, search))
        tickets = cursor.fetchall()

        return jsonify(tickets), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# GET BY ID
@tickets_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
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

        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404

        return jsonify(ticket), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# UPDATE
@tickets_bp.route("/tickets/<int:ticket_id>", methods=["PUT"])
def update_ticket(ticket_id):
    connection = None
    cursor = None

    try:
        data = request.get_json()

        allowed = {
            "title": "Title",
            "description": "Description",
            "assigned_to": "Assigned_To",
            "category": "Category",
            "status": "Status",
            "priority": "Priority"
        }

        fields = []
        values = []

        for key, column in allowed.items():
            if key in data:
                fields.append(f"{column} = %s")
                values.append(data[key])

        if not fields:
            return jsonify({"error": "No fields to update"}), 400

        values.append(ticket_id)

        query = f"""
            UPDATE TICKET
            SET {", ".join(fields)}
            WHERE ID = %s
        """

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query, values)
        connection.commit()

        cursor.execute(
            "SELECT * FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        ticket = cursor.fetchone()

        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404

        return jsonify(ticket), 200

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# DELETE
@tickets_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Ticket not found"}), 404

        connection.commit()

        return jsonify({
            "message": "Ticket deleted successfully"
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({"error": str(error)}), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()