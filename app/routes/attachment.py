import os
import uuid
import mysql.connector

from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from firebase_admin import firestore

from app import db
from app.config import DB_CONFIG
from app.routes.auth import token_required


attachment_bp = Blueprint(
    "attachment",
    __name__,
    url_prefix="/attachments"
)


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)


# =========================================================
# UPLOAD ATTACHMENT
# =========================================================

@attachment_bp.route(
    "/upload/<int:ticket_id>",
    methods=["POST"]
)
@token_required
def upload_attachment(ticket_id):

    if "file" not in request.files:

        return jsonify({
            "message": "File is required"
        }), 400


    file = request.files["file"]


    if file.filename == "":

        return jsonify({
            "message": "No file selected"
        }), 400


    user_email = g.current_user.get(
        "email"
    )


    if not user_email:

        return jsonify({
            "message": "User email not found"
        }), 401


    connection = None
    cursor = None
    full_path = None


    try:

        connection = mysql.connector.connect(
            **DB_CONFIG
        )

        cursor = connection.cursor(
            dictionary=True
        )


        # =====================================================
        # GET USER
        # =====================================================

        cursor.execute(
            """
            SELECT ID
            FROM `USER`
            WHERE Email = %s
            """,
            (user_email,)
        )

        user = cursor.fetchone()


        if not user:

            return jsonify({
                "message":
                    "User not found in database"
            }), 404


        uploaded_by = user["ID"]


        # =====================================================
        # CHECK TICKET
        # =====================================================

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


        # =====================================================
        # SAVE FILE
        # =====================================================

        original_name = secure_filename(
            file.filename
        )


        unique_name = (
            f"{uuid.uuid4()}_{original_name}"
        )


        ticket_folder = os.path.join(
            UPLOAD_FOLDER,
            "tickets",
            str(ticket_id)
        )


        os.makedirs(
            ticket_folder,
            exist_ok=True
        )


        full_path = os.path.join(
            ticket_folder,
            unique_name
        )


        file.save(full_path)


        # URL / path used by the application
        attachment_url = (
            f"/uploads/tickets/"
            f"{ticket_id}/"
            f"{unique_name}"
        )


        # =====================================================
        # SAVE ATTACHMENT IN MYSQL
        # =====================================================

        cursor.execute(
            """
            INSERT INTO ATTACHMENT
            (
                File_Name,
                File_Path,
                Ticket_ID,
                Uploaded_By
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                original_name,
                attachment_url,
                ticket_id,
                uploaded_by
            )
        )


        mysql_attachment_id = (
            cursor.lastrowid
        )


        # =====================================================
        # SAVE ATTACHMENT IN FIRESTORE
        # =====================================================

        attachment_ref = (
            db.collection("attachments")
            .document()
        )


        attachment_data = {

            "ID":
                attachment_ref.id,

            "MySQL_ID":
                mysql_attachment_id,

            "File_Name":
                original_name,

            "File_Path":
                attachment_url,

            "Ticket_ID":
                ticket_id,

            "Uploaded_By":
                uploaded_by,

            "Created_At":
                firestore.SERVER_TIMESTAMP
        }


        attachment_ref.set(
            attachment_data
        )


        # Save MySQL transaction
        connection.commit()


        # =====================================================
        # RESPONSE
        # =====================================================

        return jsonify({

            "message":
                "Attachment uploaded successfully",

            "attachment_id":
                mysql_attachment_id,

            "firestore_id":
                attachment_ref.id,

            "file_name":
                original_name,

            "file_url":
                attachment_url,

            "ticket_id":
                ticket_id,

            "uploaded_by":
                uploaded_by

        }), 201


    except mysql.connector.Error as error:

        if connection:
            connection.rollback()

        return jsonify({
            "message":
                "Database operation failed",

            "error":
                str(error)
        }), 500


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "message":
                "Attachment upload failed",

            "error":
                str(error)
        }), 500


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()