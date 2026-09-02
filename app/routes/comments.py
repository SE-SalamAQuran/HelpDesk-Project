from flask import Blueprint, request, jsonify, g

from app.config import get_db_connection
from app.routes.auth import (
    token_required,
    permission_required,
    sync_user_with_database
)


comments_bp = Blueprint(
    "comments",
    __name__
)


# =========================================================
# GET COMMENTS
# =========================================================

@comments_bp.route(
    "/tickets/<int:ticket_id>/comments",
    methods=["GET"]
)
@token_required
def get_comments(ticket_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # Check ticket exists
        cursor.execute(
            """
            SELECT ID
            FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )

        ticket = cursor.fetchone()

        if not ticket:

            return jsonify({
                "message": "Ticket not found"
            }), 404


        # Get comments
        cursor.execute(
            """
            SELECT
                c.ID,
                c.Ticket_ID,
                c.User_ID,
                c.Comment_Text,
                c.Created_At,
                c.Modified_At,

                u.Full_Name AS User_Name,
                u.Email AS User_Email,
                u.Role AS User_Role

            FROM `COMMENT` c

            LEFT JOIN `USER` u
                ON c.User_ID = u.ID

            WHERE c.Ticket_ID = %s

            ORDER BY c.Created_At ASC
            """,
            (ticket_id,)
        )


        comments = cursor.fetchall()


        return jsonify({
            "ticket_id": ticket_id,
            "comments": comments
        }), 200


    except Exception as error:

        return jsonify({
            "message": str(error)
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
# ADD COMMENT
# =========================================================

@comments_bp.route(
    "/tickets/<int:ticket_id>/comments",
    methods=["POST"]
)
@permission_required("add_comment")
def add_comment(ticket_id):

    connection = None
    cursor = None

    try:

        data = request.get_json() or {}

        text = (
            data.get("text")
            or ""
        ).strip()


        if not text:

            return jsonify({
                "message": "Comment text is required"
            }), 400


        email = g.current_user.get(
            "email"
        )


        if not email:

            return jsonify({
                "message":
                "User email not found in token"
            }), 401


        # Get MySQL user ID
        user_id = sync_user_with_database(
            email=email,
            role=g.current_user.get(
                "role",
                "employee"
            ),
            full_name=g.current_user.get(
                "name"
            )
        )


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # Check ticket exists
        cursor.execute(
            """
            SELECT ID
            FROM TICKET
            WHERE ID = %s
            """,
            (ticket_id,)
        )

        ticket = cursor.fetchone()


        if not ticket:

            return jsonify({
                "message": "Ticket not found"
            }), 404


        # Insert comment
        cursor.execute(
            """
            INSERT INTO `COMMENT`
            (
                Comment_Text,
                User_ID,
                Ticket_ID
            )
            VALUES (%s, %s, %s)
            """,
            (
                text,
                user_id,
                ticket_id
            )
        )


        connection.commit()

        comment_id = cursor.lastrowid


        # Return new comment
        cursor.execute(
            """
            SELECT
                c.ID,
                c.Ticket_ID,
                c.User_ID,
                c.Comment_Text,
                c.Created_At,
                c.Modified_At,

                u.Full_Name AS User_Name,
                u.Email AS User_Email,
                u.Role AS User_Role

            FROM `COMMENT` c

            LEFT JOIN `USER` u
                ON c.User_ID = u.ID

            WHERE c.ID = %s
            """,
            (comment_id,)
        )


        comment = cursor.fetchone()


        return jsonify({
            "message":
            "Comment added successfully",

            "comment":
            comment

        }), 201


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "message": str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()