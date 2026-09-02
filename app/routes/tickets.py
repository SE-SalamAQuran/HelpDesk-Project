import mysql.connector

from flask import Blueprint, jsonify, request, g
from datetime import date, datetime, timedelta

from app.config import get_db_connection
from app.routes.auth import (
    token_required,
    permission_required,
    sync_user_with_database
)


tickets_bp = Blueprint(
    "tickets",
    __name__
)


# =========================================================
# HELPER: GET CURRENT MYSQL USER
# =========================================================

def get_current_user():

    email = g.current_user.get("email")

    role = g.current_user.get(
        "role",
        "employee"
    )

    user_id = sync_user_with_database(
        email=email,
        role=role,
        full_name=g.current_user.get("name")
    )

    return user_id, role


# =========================================================
# GET ALL TICKETS
# employee -> own tickets only
# IT/admin -> all tickets
# =========================================================

@tickets_bp.route(
    "/api/tickets",
    methods=["GET"]
)
@token_required
def get_tickets():

    connection = None
    cursor = None

    try:

        user_id, role = get_current_user()

        category = request.args.get("category")
        status = request.args.get("status")
        created_by = request.args.get("created_by")
        priority = request.args.get("priority")
        created_date = request.args.get("created_date")

        from_date = request.args.get(
            "from_date",
            (date.today() - timedelta(days=90)).isoformat()
        )

        to_date = request.args.get(
            "to_date",
            date.today().isoformat()
        )

        # If frontend sends one specific date
        if created_date:
            from_date = created_date
            to_date = created_date


        try:

            start = datetime.strptime(
                from_date,
                "%Y-%m-%d"
            ).date()

            end = datetime.strptime(
                to_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return jsonify({
                "error":
                "Date must be YYYY-MM-DD"
            }), 400


        if start > end:

            return jsonify({
                "error":
                "from_date must be before to_date"
            }), 400


        page = request.args.get(
            "page",
            1,
            type=int
        )

        per_page = request.args.get(
            "per_page",
            10,
            type=int
        )


        if page < 1:
            page = 1

        if per_page < 1:
            per_page = 10


        offset = (
            page - 1
        ) * per_page


        query = """
            SELECT *
            FROM TICKET
            WHERE 1=1
        """

        count_query = """
            SELECT COUNT(*) AS total
            FROM TICKET
            WHERE 1=1
        """

        conditions = ""
        values = []


        # -------------------------------------------------
        # EMPLOYEE CAN ONLY SEE OWN TICKETS
        # -------------------------------------------------

        if role == "employee":

            conditions += """
                AND Created_By = %s
            """

            values.append(
                user_id
            )

        # Admin / IT can filter by creator
        elif created_by:

            conditions += """
                AND Created_By = %s
            """

            values.append(
                created_by
            )


        if category:

            conditions += """
                AND Category = %s
            """

            values.append(
                category
            )


        if status:

            conditions += """
                AND Status = %s
            """

            values.append(
                status
            )


        if priority:

            conditions += """
                AND Priority = %s
            """

            values.append(
                priority
            )


        conditions += """
            AND DATE(Created_At)
            BETWEEN %s AND %s
        """

        values.extend([
            from_date,
            to_date
        ])


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            count_query + conditions,
            values
        )

        total = cursor.fetchone()[
            "total"
        ]


        query += (
            conditions
            + """
            ORDER BY ID DESC
            LIMIT %s OFFSET %s
            """
        )


        cursor.execute(
            query,
            values + [
                per_page,
                offset
            ]
        )


        tickets = cursor.fetchall()


        total_pages = (
            total + per_page - 1
        ) // per_page


        return jsonify({

            "page":
            page,

            "per_page":
            per_page,

            "total_tickets":
            total,

            "total_pages":
            total_pages,

            "has_next":
            page < total_pages,

            "tickets":
            tickets

        }), 200


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# CREATE TICKET
# Created_By comes from JWT
# not from frontend
# =========================================================

@tickets_bp.route(
    "/tickets",
    methods=["POST"]
)
@permission_required("create_ticket")
def create_ticket():

    connection = None
    cursor = None

    try:

        data = request.get_json() or {}

        title = (
            data.get("title")
            or ""
        ).strip()


        if not title:

            return jsonify({
                "error":
                "title is required"
            }), 400


        user_id, role = get_current_user()


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

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """


        values = (

            title,

            data.get("description"),

            user_id,

            data.get("assigned_to"),

            data.get(
                "category",
                "HR"
            ),

            "Open",

            data.get(
                "priority",
                "Medium"
            )
        )


        connection = get_db_connection()

        cursor = connection.cursor()


        cursor.execute(
            query,
            values
        )

        connection.commit()


        ticket_id = (
            cursor.lastrowid
        )


        return jsonify({

            "ID":
            ticket_id,

            "title":
            title,

            "description":
            data.get("description"),

            "created_by":
            user_id,

            "category":
            data.get(
                "category",
                "HR"
            ),

            "status":
            "Open",

            "priority":
            data.get(
                "priority",
                "Medium"
            )

        }), 201


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# SEARCH TICKETS
# employee -> own only
# IT/admin -> all
# =========================================================

@tickets_bp.route(
    "/tickets/search",
    methods=["GET"]
)
@token_required
def search_tickets():

    connection = None
    cursor = None

    try:

        user_id, role = get_current_user()

        word = (
            request.args.get("q")
            or ""
        ).strip()


        if not word:

            return jsonify({
                "error":
                "Search word is required"
            }), 400


        search = f"%{word}%"


        category = request.args.get(
            "category"
        )

        status = request.args.get(
            "status"
        )

        priority = request.args.get(
            "priority"
        )

        created_by = request.args.get(
            "created_by"
        )

        created_date = request.args.get(
            "created_date"
        )


        page = request.args.get(
            "page",
            1,
            type=int
        )

        per_page = request.args.get(
            "per_page",
            10,
            type=int
        )


        if page < 1:
            page = 1

        if per_page < 1:
            per_page = 10


        offset = (
            page - 1
        ) * per_page


        base_from = """
            FROM TICKET t

            LEFT JOIN `USER` u
                ON t.Created_By = u.ID

            WHERE (
                t.Title LIKE %s
                OR t.Description LIKE %s
                OR u.Full_Name LIKE %s
                OR CAST(
                    t.Created_By AS CHAR
                ) LIKE %s
            )
        """


        values = [
            search,
            search,
            search,
            search
        ]

        conditions = ""


        # Employee only own tickets
        if role == "employee":

            conditions += """
                AND t.Created_By = %s
            """

            values.append(
                user_id
            )

        elif created_by:

            conditions += """
                AND t.Created_By = %s
            """

            values.append(
                created_by
            )


        if category:

            conditions += """
                AND t.Category = %s
            """

            values.append(
                category
            )


        if status:

            conditions += """
                AND t.Status = %s
            """

            values.append(
                status
            )


        if priority:

            conditions += """
                AND t.Priority = %s
            """

            values.append(
                priority
            )


        if created_date:

            conditions += """
                AND DATE(t.Created_At) = %s
            """

            values.append(
                created_date
            )


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        count_query = (
            "SELECT COUNT(*) AS total "
            + base_from
            + conditions
        )


        cursor.execute(
            count_query,
            values
        )


        total = cursor.fetchone()[
            "total"
        ]


        query = (
            """
            SELECT
                t.*,
                u.Full_Name
                    AS Created_By_Name
            """
            + base_from
            + conditions
            + """
            ORDER BY t.ID DESC
            LIMIT %s OFFSET %s
            """
        )


        cursor.execute(
            query,
            values + [
                per_page,
                offset
            ]
        )


        tickets = cursor.fetchall()


        total_pages = (
            total + per_page - 1
        ) // per_page


        return jsonify({

            "page":
            page,

            "per_page":
            per_page,

            "total_tickets":
            total,

            "total_pages":
            total_pages,

            "has_next":
            page < total_pages,

            "tickets":
            tickets

        }), 200


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# GET TICKET BY ID
# employee -> own ticket only
# IT/admin -> any
# =========================================================

@tickets_bp.route(
    "/tickets/<int:ticket_id>",
    methods=["GET"]
)
@token_required
def get_ticket(ticket_id):

    connection = None
    cursor = None

    try:

        user_id, role = get_current_user()


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT *
            FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )


        ticket = cursor.fetchone()


        if not ticket:

            return jsonify({
                "error":
                "Ticket not found"
            }), 404


        # Employee cannot open another user's ticket
        if (
            role == "employee"
            and ticket["Created_By"] != user_id
        ):

            return jsonify({
                "error":
                "You are not allowed to view this ticket"
            }), 403


        return jsonify(
            ticket
        ), 200


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# UPDATE
# IT / ADMIN ONLY
# =========================================================

@tickets_bp.route(
    "/tickets/<int:ticket_id>",
    methods=["PUT"]
)
@permission_required("update_ticket")
def update_ticket(ticket_id):

    connection = None
    cursor = None

    try:

        data = request.get_json() or {}


        allowed = {

            "title":
            "Title",

            "description":
            "Description",

            "assigned_to":
            "Assigned_To",

            "category":
            "Category",

            "status":
            "Status",

            "priority":
            "Priority"
        }


        fields = []
        values = []


        for key, column in allowed.items():

            if key in data:

                fields.append(
                    f"{column} = %s"
                )

                values.append(
                    data[key]
                )


        if not fields:

            return jsonify({
                "error":
                "No fields to update"
            }), 400


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # Make sure ticket exists
        cursor.execute(
            """
            SELECT ID
            FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )


        if not cursor.fetchone():

            return jsonify({
                "error":
                "Ticket not found"
            }), 404


        values.append(
            ticket_id
        )


        query = f"""
            UPDATE TICKET

            SET {
                ", ".join(fields)
            }

            WHERE ID = %s
        """


        cursor.execute(
            query,
            values
        )


        connection.commit()


        cursor.execute(
            """
            SELECT *
            FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )


        ticket = cursor.fetchone()


        return jsonify(
            ticket
        ), 200


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "error": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# DELETE
# ADMIN ONLY
# =========================================================

@tickets_bp.route(
    "/tickets/<int:ticket_id>",
    methods=["DELETE"]
)
@permission_required("delete_ticket")
def delete_ticket(ticket_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()


        cursor.execute(
            """
            DELETE FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )


        if cursor.rowcount == 0:

            return jsonify({
                "error":
                "Ticket not found"
            }), 404


        connection.commit()


        return jsonify({
            "message":
            "Ticket deleted successfully"
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

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()