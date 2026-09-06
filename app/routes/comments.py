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
# GET CURRENT MYSQL USER
# =========================================================

def get_current_user_id():

    email = g.current_user.get("email")

    if not email:
        return None

    return sync_user_with_database(
        email=email,
        role=g.current_user.get(
            "role",
            "employee"
        ),
        full_name=g.current_user.get("name")
    )


# =========================================================
# ADD CHANGE LOG
# =========================================================

def add_change_log(
    cursor,
    field_name,
    old_value,
    new_value,
    ticket_id,
    changed_by
):

    cursor.execute(
        """
        INSERT INTO CHANGE_LOG
        (
            Field_Name,
            Old_Value,
            New_Value,
            Ticket_ID,
            Changed_By
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            field_name,
            old_value,
            new_value,
            ticket_id,
            changed_by
        )
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


        user_id = get_current_user_id()

        if not user_id:

            return jsonify({
                "message":
                    "User email not found in token"
            }), 401


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


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

        comment_id = cursor.lastrowid


        add_change_log(
            cursor=cursor,
            field_name=f"Comment #{comment_id} Created",
            old_value=None,
            new_value=text,
            ticket_id=ticket_id,
            changed_by=user_id
        )


        connection.commit()


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
            # =========================================================
# GET COMMENT BY ID
# =========================================================

@comments_bp.route(
    "/comments/<int:comment_id>",
    methods=["GET"]
)
@token_required
def get_comment(comment_id):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

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

        if not comment:

            return jsonify({
                "message": "Comment not found"
            }), 404


        return jsonify({
            "comment": comment
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
# EDIT COMMENT
# =========================================================

@comments_bp.route(
    "/comments/<int:comment_id>",
    methods=["PUT"]
)
@permission_required("add_comment")
def edit_comment(comment_id):

    connection = None
    cursor = None

    try:

        data = request.get_json() or {}

        new_text = (
            data.get("text")
            or ""
        ).strip()

        if not new_text:

            return jsonify({
                "message": "Comment text is required"
            }), 400


        current_user_id = get_current_user_id()

        if not current_user_id:

            return jsonify({
                "message":
                    "User email not found in token"
            }), 401


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT
                ID,
                Ticket_ID,
                User_ID,
                Comment_Text
            FROM `COMMENT`
            WHERE ID = %s
            """,
            (comment_id,)
        )

        comment = cursor.fetchone()

        if not comment:

            return jsonify({
                "message": "Comment not found"
            }), 404


        current_role = g.current_user.get(
            "role",
            "employee"
        )


        if (
            comment["User_ID"] != current_user_id
            and current_role not in ["admin", "IT"]
        ):

            return jsonify({
                "message":
                    "You cannot edit this comment"
            }), 403


        old_text = comment["Comment_Text"]
        ticket_id = comment["Ticket_ID"]


        cursor.execute(
            """
            UPDATE `COMMENT`
            SET
                Comment_Text = %s,
                Modified_At = CURRENT_TIMESTAMP
            WHERE ID = %s
            """,
            (
                new_text,
                comment_id
            )
        )


        add_change_log(
            cursor=cursor,
            field_name=f"Comment #{comment_id} Updated",
            old_value=old_text,
            new_value=new_text,
            ticket_id=ticket_id,
            changed_by=current_user_id
        )


        connection.commit()


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

        updated_comment = cursor.fetchone()


        return jsonify({
            "message":
                "Comment updated successfully",
            "comment":
                updated_comment
        }), 200


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
            # =========================================================
# DELETE COMMENT
# =========================================================

@comments_bp.route(
    "/comments/<int:comment_id>",
    methods=["DELETE"]
)
@permission_required("add_comment")
def delete_comment(comment_id):

    connection = None
    cursor = None

    try:

        current_user_id = get_current_user_id()

        if not current_user_id:

            return jsonify({
                "message":
                    "User email not found in token"
            }), 401


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT
                ID,
                Ticket_ID,
                User_ID,
                Comment_Text
            FROM `COMMENT`
            WHERE ID = %s
            """,
            (comment_id,)
        )

        comment = cursor.fetchone()

        if not comment:

            return jsonify({
                "message": "Comment not found"
            }), 404


        current_role = g.current_user.get(
            "role",
            "employee"
        )


        if (
            comment["User_ID"] != current_user_id
            and current_role not in ["admin", "IT"]
        ):

            return jsonify({
                "message":
                    "You cannot delete this comment"
            }), 403


        old_text = comment["Comment_Text"]
        ticket_id = comment["Ticket_ID"]


        cursor.execute(
            """
            DELETE FROM `COMMENT`
            WHERE ID = %s
            """,
            (comment_id,)
        )


        add_change_log(
            cursor=cursor,
            field_name=f"Comment #{comment_id} Deleted",
            old_value=old_text,
            new_value=None,
            ticket_id=ticket_id,
            changed_by=current_user_id
        )


        connection.commit()


        return jsonify({
            "message":
                "Comment deleted successfully"
        }), 200


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