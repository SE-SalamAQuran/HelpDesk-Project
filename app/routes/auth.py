import os
import requests

from functools import wraps
from urllib.parse import urlencode

from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth

from app.config import get_db_connection


load_dotenv()


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


FIREBASE_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")


# =========================================================
# ROLE PERMISSIONS
# =========================================================

ROLE_PERMISSIONS = {

    "admin": [
        "create_ticket",
        "view_all_tickets",
        "update_ticket",
        "delete_ticket",
        "assign_ticket",
        "add_comment",
        "manage_users"
    ],

    "IT": [
        "view_all_tickets",
        "update_ticket",
        "assign_ticket",
        "add_comment"
    ],

    "employee": [
        "create_ticket",
        "view_own_tickets",
        "add_comment"
    ]
}


# =========================================================
# SET FIREBASE ROLE + PERMISSIONS
# =========================================================

def set_user_permissions(uid, role="employee"):

    permissions = ROLE_PERMISSIONS.get(
        role,
        ROLE_PERMISSIONS["employee"]
    )

    firebase_auth.set_custom_user_claims(
        uid,
        {
            "role": role,
            "permissions": permissions
        }
    )

    return permissions


# =========================================================
# REFRESH FIREBASE TOKEN
# =========================================================

def refresh_firebase_token(refresh_token):

    url = (
        "https://securetoken.googleapis.com/v1/"
        f"token?key={FIREBASE_API_KEY}"
    )

    try:

        response = requests.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            },
            timeout=10
        )

        result = response.json()

        if response.status_code != 200:
            return None

        return result

    except requests.RequestException:
        return None


# =========================================================
# TOKEN REQUIRED
# =========================================================

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get(
            "Authorization"
        )

        if not auth_header:

            return jsonify({
                "message":
                "Authorization token is required"
            }), 401


        if not auth_header.startswith(
            "Bearer "
        ):

            return jsonify({
                "message":
                "Invalid authorization format"
            }), 401


        token = auth_header.split(
            "Bearer ",
            1
        )[1].strip()


        try:

            decoded_token = (
                firebase_auth.verify_id_token(
                    token
                )
            )

            g.current_user = decoded_token

        except Exception:

            return jsonify({
                "message":
                "Invalid or expired token"
            }), 401


        return f(*args, **kwargs)

    return decorated


# =========================================================
# PERMISSION REQUIRED
# =========================================================

def permission_required(permission):

    def decorator(f):

        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):

            user = g.current_user

            permissions = user.get(
                "permissions",
                []
            )

            if permission not in permissions:

                return jsonify({
                    "message":
                    "Permission denied"
                }), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


# =========================================================
# SYNC FIREBASE USER WITH MYSQL
# =========================================================

def sync_user_with_database(
    email,
    role="employee",
    full_name=None
):

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT ID, Role
            FROM `USER`
            WHERE Email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()


        # USER ALREADY EXISTS
        if user:

            # Keep MySQL role synchronized
            if user["Role"] != role:

                cursor.execute(
                    """
                    UPDATE `USER`
                    SET Role = %s
                    WHERE ID = %s
                    """,
                    (
                        role,
                        user["ID"]
                    )
                )

                connection.commit()

            return user["ID"]


        # CREATE NEW USER
        cursor.execute(
            """
            INSERT INTO `USER`
            (
                Full_Name,
                Email,
                Password,
                Role
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                full_name
                or email.split("@")[0],

                email,

                "FIREBASE_AUTH",

                role
            )
        )

        connection.commit()

        return cursor.lastrowid


    finally:

        if cursor:
            cursor.close()

        if (
            connection
            and connection.is_connected()
        ):
            connection.close()


# =========================================================
# SIGNUP
# =========================================================

@auth_bp.route(
    "/signup",
    methods=["POST"]
)
def signup():

    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")


    if not email or not password:

        return jsonify({
            "message":
            "Email and password are required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signUp?key={FIREBASE_API_KEY}"
    )


    payload = {

        "email": email,

        "password": password,

        "returnSecureToken": True
    }


    try:

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        result = response.json()

    except requests.RequestException:

        return jsonify({
            "message":
            "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message":
            result.get(
                "error",
                {}
            ).get(
                "message",
                "Signup failed"
            )
        }), 400


    uid = result.get("localId")

    # Every new user starts as employee
    role = "employee"


    # Save user in MySQL
    user_id = sync_user_with_database(
        email=result.get("email"),
        role=role
    )


    # Add Firebase role + permissions
    permissions = set_user_permissions(
        uid,
        role
    )


    # Refresh token so new claims appear
    refreshed = refresh_firebase_token(
        result.get("refreshToken")
    )


    if not refreshed:

        return jsonify({
            "message":
            "Account created but token refresh failed"
        }), 500


    return jsonify({

        "message":
        "Account created successfully",

        "user_id":
        user_id,

        "uid":
        uid,

        "email":
        result.get("email"),

        "role":
        role,

        "permissions":
        permissions,

        "access_token":
        refreshed.get("id_token"),

        "refresh_token":
        refreshed.get("refresh_token")

    }), 201


# =========================================================
# LOGIN
# =========================================================

@auth_bp.route(
    "/login",
    methods=["POST"]
)
def login():

    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")


    if not email or not password:

        return jsonify({
            "message":
            "Email and password are required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )


    payload = {

        "email":
        email,

        "password":
        password,

        "returnSecureToken":
        True
    }


    try:

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        result = response.json()

    except requests.RequestException:

        return jsonify({
            "message":
            "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message":
            result.get(
                "error",
                {}
            ).get(
                "message",
                "Login failed"
            )
        }), 401


    uid = result.get("localId")


    user_record = firebase_auth.get_user(
        uid
    )

    claims = (
        user_record.custom_claims
        or {}
    )


    role = claims.get(
        "role"
    ) or "employee"


    permissions = claims.get(
        "permissions"
    )


    expected_permissions = (
        ROLE_PERMISSIONS.get(
            role,
            ROLE_PERMISSIONS["employee"]
        )
    )


    # Update claims when missing or outdated
    if permissions != expected_permissions:

        permissions = set_user_permissions(
            uid,
            role
        )

        refreshed = refresh_firebase_token(
            result.get("refreshToken")
        )


        if not refreshed:

            return jsonify({
                "message":
                "Login successful but token refresh failed"
            }), 500


        access_token = refreshed.get(
            "id_token"
        )

        refresh_token = refreshed.get(
            "refresh_token"
        )


    else:

        access_token = result.get(
            "idToken"
        )

        refresh_token = result.get(
            "refreshToken"
        )


    # Sync Firebase user with MySQL
    user_id = sync_user_with_database(
        email=result.get("email"),
        role=role
    )


    return jsonify({

        "message":
        "Login successful",

        "user_id":
        user_id,

        "uid":
        uid,

        "email":
        result.get("email"),

        "role":
        role,

        "permissions":
        permissions,

        "access_token":
        access_token,

        "refresh_token":
        refresh_token

    }), 200


# =========================================================
# RESET PASSWORD
# =========================================================

@auth_bp.route(
    "/reset-password",
    methods=["POST"]
)
def reset_password():

    data = request.get_json() or {}

    email = data.get("email")


    if not email:

        return jsonify({
            "message":
            "Email is required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:sendOobCode"
        f"?key={FIREBASE_API_KEY}"
    )


    payload = {

        "requestType":
        "PASSWORD_RESET",

        "email":
        email
    }


    try:

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        result = response.json()

    except requests.RequestException:

        return jsonify({
            "message":
            "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message":
            result.get(
                "error",
                {}
            ).get(
                "message",
                "Password reset failed"
            )
        }), 400


    return jsonify({
        "message":
        "Password reset email sent successfully"
    }), 200


# =========================================================
# GOOGLE SIGN IN
# =========================================================

@auth_bp.route(
    "/google-signin",
    methods=["POST"]
)
def google_sign_in():

    data = request.get_json() or {}

    google_id_token = data.get(
        "id_token"
    )


    if not google_id_token:

        return jsonify({
            "message":
            "Google ID token is required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithIdp"
        f"?key={FIREBASE_API_KEY}"
    )


    post_body = urlencode({

        "id_token":
        google_id_token,

        "providerId":
        "google.com"
    })


    payload = {

        "postBody":
        post_body,

        "requestUri":
        "http://localhost",

        "returnIdpCredential":
        True,

        "returnSecureToken":
        True
    }


    try:

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        result = response.json()

    except requests.RequestException:

        return jsonify({
            "message":
            "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message":
            result.get(
                "error",
                {}
            ).get(
                "message",
                "Google sign in failed"
            )
        }), 400


    uid = result.get("localId")


    user_record = firebase_auth.get_user(
        uid
    )

    claims = (
        user_record.custom_claims
        or {}
    )


    role = claims.get(
        "role"
    ) or "employee"


    permissions = claims.get(
        "permissions"
    )


    expected_permissions = (
        ROLE_PERMISSIONS.get(
            role,
            ROLE_PERMISSIONS["employee"]
        )
    )


    if permissions != expected_permissions:

        permissions = set_user_permissions(
            uid,
            role
        )

        refreshed = refresh_firebase_token(
            result.get("refreshToken")
        )


        if not refreshed:

            return jsonify({
                "message":
                "Google login successful but token refresh failed"
            }), 500


        access_token = refreshed.get(
            "id_token"
        )

        refresh_token = refreshed.get(
            "refresh_token"
        )


    else:

        access_token = result.get(
            "idToken"
        )

        refresh_token = result.get(
            "refreshToken"
        )


    user_id = sync_user_with_database(

        email=result.get("email"),

        role=role,

        full_name=result.get(
            "displayName"
        )
    )


    return jsonify({

        "message":
        "Google sign in successful",

        "user_id":
        user_id,

        "uid":
        uid,

        "email":
        result.get("email"),

        "name":
        result.get("displayName"),

        "role":
        role,

        "permissions":
        permissions,

        "access_token":
        access_token,

        "refresh_token":
        refresh_token

    }), 200


# =========================================================
# CHANGE USER ROLE
# ADMIN ONLY
# =========================================================

@auth_bp.route(
    "/set-role",
    methods=["PUT"]
)
@permission_required("manage_users")
def set_role():

    data = request.get_json() or {}

    email = data.get("email")
    new_role = data.get("role")


    allowed_roles = [
        "admin",
        "IT",
        "employee"
    ]


    if not email or not new_role:

        return jsonify({
            "message":
            "Email and role are required"
        }), 400


    if new_role not in allowed_roles:

        return jsonify({
            "message":
            "Invalid role"
        }), 400


    connection = None
    cursor = None


    try:

        # -------------------------------------------------
        # Check Firebase user
        # -------------------------------------------------

        user_record = (
            firebase_auth.get_user_by_email(
                email
            )
        )


        # -------------------------------------------------
        # Make sure user exists in MySQL
        # -------------------------------------------------

        user_id = sync_user_with_database(

            email=email,

            role=(
                user_record.custom_claims
                or {}
            ).get(
                "role",
                "employee"
            ),

            full_name=(
                user_record.display_name
            )
        )


        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # -------------------------------------------------
        # ONLY ONE ADMIN
        # -------------------------------------------------

        if new_role == "admin":

            cursor.execute(
                """
                SELECT ID, Email
                FROM `USER`
                WHERE Role = 'admin'
                AND Email != %s
                LIMIT 1
                """,
                (email,)
            )

            existing_admin = (
                cursor.fetchone()
            )


            if existing_admin:

                return jsonify({
                    "message":
                    "Only one admin is allowed"
                }), 409


        # -------------------------------------------------
        # UPDATE MYSQL ROLE
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE `USER`
            SET Role = %s
            WHERE ID = %s
            """,
            (
                new_role,
                user_id
            )
        )

        connection.commit()


        # -------------------------------------------------
        # UPDATE FIREBASE CLAIMS
        # -------------------------------------------------

        permissions = ROLE_PERMISSIONS[
            new_role
        ]


        firebase_auth.set_custom_user_claims(
            user_record.uid,
            {
                "role":
                new_role,

                "permissions":
                permissions
            }
        )


        return jsonify({

            "message":
            "User role updated successfully",

            "user_id":
            user_id,

            "email":
            email,

            "role":
            new_role,

            "permissions":
            permissions

        }), 200


    except firebase_auth.UserNotFoundError:

        return jsonify({
            "message":
            "Firebase user not found"
        }), 404


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "message":
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


# =========================================================
# PROFILE
# =========================================================

@auth_bp.route(
    "/profile",
    methods=["GET"]
)
@token_required
def get_user_profile():

    user = g.current_user


    return jsonify({

        "message":
        "User profile retrieved successfully",

        "uid":
        user.get("uid"),

        "email":
        user.get("email"),

        "name":
        user.get("name"),

        "role":
        user.get(
            "role",
            "employee"
        ),

        "permissions":
        user.get(
            "permissions",
            []
        ),

        "email_verified":
        user.get(
            "email_verified",
            False
        )

    }), 200