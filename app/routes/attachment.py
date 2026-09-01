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

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")


@attachment_bp.route("/upload/<int:ticket_id>", methods=["POST"])
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


    user_email = g.current_user.get("email")

    if not user_email:
        return jsonify({
            "message": "User email not found"
        }), 401


    connection = None
    cursor = None

    try:

        connection = mysql.connector.connect(**DB_CONFIG)

        cursor = connection.cursor(dictionary=True)


        cursor.execute(
            "SELECT ID FROM `USER` WHERE Email = %s",
            (user_email,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "message": "User not found in database"
            }), 404

        uploaded_by = user["ID"]


        cursor.execute(
            "SELECT ID FROM TICKET WHERE ID = %s",
            (ticket_id,)
        )

        ticket = cursor.fetchone()

        if not ticket:
            return jsonify({
                "message": "Ticket not found"
            }), 404


        original_name = secure_filename(file.filename)

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

        relative_path = (
            f"/uploads/tickets/"
            f"{ticket_id}/"
            f"{unique_name}"
        )


        attachment_ref = (
            db.collection("attachments")
            .document()
        )

        attachment_data = {
            "ID": attachment_ref.id,
            "File_Name": original_name,
            "File_Path": relative_path,
            "Ticket_ID": ticket_id,
            "Uploaded_By": uploaded_by,
            "Created_At": firestore.SERVER_TIMESTAMP
        }

        attachment_ref.set(attachment_data)


        return jsonify({
            "message": "Attachment uploaded successfully",
            "attachment_id": attachment_ref.id,
            "file_name": original_name,
            "file_path": relative_path,
            "ticket_id": ticket_id,
            "uploaded_by": uploaded_by
        }), 201


    except mysql.connector.Error as error:
        return jsonify({
            "message": "Database connection failed",
            "error": str(error)
        }), 500

    except Exception as error:
        return jsonify({
            "message": "Attachment upload failed",
            "error": str(error)
        }), 500


    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()