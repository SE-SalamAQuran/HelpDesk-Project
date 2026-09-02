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
# ONLY THIS EMAIL CAN BE ADMIN
# =========================================================

MAIN_ADMIN_EMAIL = "omar.qaisi735@gmail.com"


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
# GET CORRECT ROLE
# =========================================================

def get_correct_role(email, requested_role="employee"):

    email = (email or "").lower().strip()

    # Main admin is always admin
    if email == MAIN_ADMIN_EMAIL.lower():
        return "admin"

    # Nobody else can ever be admin
    if requested_role == "admin":
        return "employee"

    if requested_role not in ["employee", "IT"]:
        return "employee"

    return requested_role


# =========================================================
# SET FIREBASE PERMISSIONS
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

    if not refresh_token:
        return None

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

        auth_header = request.headers.get("Authorization")

        if not auth_header:

            return jsonify({
                "message": "Authorization token is required"
            }), 401


        if not auth_header.startswith("Bearer "):

            return jsonify({
                "message": "Invalid authorization format"
            }), 401


        token = auth_header.split(
            "Bearer ",
            1
        )[1].strip()


        try:

            decoded_token = firebase_auth.verify_id_token(
                token
            )

            email = (
                decoded_token.get("email")
                or ""
            ).lower().strip()


            # Extra protection:
            # only MAIN_ADMIN_EMAIL can behave as admin
            if email == MAIN_ADMIN_EMAIL.lower():

                decoded_token["role"] = "admin"

                decoded_token["permissions"] = (
                    ROLE_PERMISSIONS["admin"]
                )

            elif decoded_token.get("role") == "admin":

                decoded_token["role"] = "employee"

                decoded_token["permissions"] = (
                    ROLE_PERMISSIONS["employee"]
                )


            g.current_user = decoded_token

        except Exception:

            return jsonify({
                "message": "Invalid or expired token"
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
                    "message": "Permission denied"
                }), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


# =========================================================
# MAIN ADMIN ONLY
# =========================================================

def main_admin_required(f):

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):

        email = (
            g.current_user.get("email")
            or ""
        ).lower().strip()

        if email != MAIN_ADMIN_EMAIL.lower():

            return jsonify({
                "message": "Admin access required"
            }), 403

        return f(*args, **kwargs)

    return decorated


# =========================================================
# SYNC USER WITH MYSQL
# =========================================================

def sync_user_with_database(
    email,
    role="employee",
    full_name=None
):

    connection = None
    cursor = None

    email = (email or "").strip()

    role = get_correct_role(
        email,
        role
    )

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                ID,
                Role
            FROM `USER`
            WHERE Email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()


        # Existing user
        if user:

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


        # New user
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
                full_name or email.split("@")[0],
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
            "message": "Email and password are required"
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
            "message": "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message": result.get(
                "error",
                {}
            ).get(
                "message",
                "Signup failed"
            )
        }), 400


    uid = result.get("localId")
    firebase_email = result.get("email")


    # Only Omar becomes admin
    role = get_correct_role(
        firebase_email,
        "employee"
    )


    user_id = sync_user_with_database(
        email=firebase_email,
        role=role
    )


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
        firebase_email,

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
            "message": "Email and password are required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
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
            "message": "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message": result.get(
                "error",
                {}
            ).get(
                "message",
                "Login failed"
            )
        }), 401


    uid = result.get("localId")

    firebase_email = result.get("email")


    user_record = firebase_auth.get_user(
        uid
    )

    claims = (
        user_record.custom_claims
        or {}
    )


    old_role = claims.get(
        "role",
        "employee"
    )


    # Force correct role
    role = get_correct_role(
        firebase_email,
        old_role
    )


    expected_permissions = (
        ROLE_PERMISSIONS[role]
    )


    old_permissions = claims.get(
        "permissions",
        []
    )


    # Update Firebase claims when needed
    if (
        old_role != role
        or old_permissions != expected_permissions
    ):

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

        permissions = expected_permissions

        access_token = result.get(
            "idToken"
        )

        refresh_token = result.get(
            "refreshToken"
        )


    user_id = sync_user_with_database(
        email=firebase_email,
        role=role,
        full_name=user_record.display_name
    )


    return jsonify({

        "message":
        "Login successful",

        "user_id":
        user_id,

        "uid":
        uid,

        "email":
        firebase_email,

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
            "message": "Email is required"
        }), 400


    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:sendOobCode"
        f"?key={FIREBASE_API_KEY}"
    )


    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
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
            "message": "Firebase connection error"
        }), 500


    if response.status_code != 200:

        return jsonify({
            "message": result.get(
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
        "id_token": google_id_token,
        "providerId": "google.com"
    })


    payload = {
        "postBody": post_body,
        "requestUri": "http://localhost",
        "returnIdpCredential": True,
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
            "message": result.get(
                "error",
                {}
            ).get(
                "message",
                "Google sign in failed"
            )
        }), 400


    uid = result.get("localId")
    firebase_email = result.get("email")


    user_record = firebase_auth.get_user(
        uid
    )

    claims = (
        user_record.custom_claims
        or {}
    )


    old_role = claims.get(
        "role",
        "employee"
    )


    role = get_correct_role(
        firebase_email,
        old_role
    )


    expected_permissions = (
        ROLE_PERMISSIONS[role]
    )


    old_permissions = claims.get(
        "permissions",
        []
    )


    if (
        old_role != role
        or old_permissions != expected_permissions
    ):

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

        permissions = expected_permissions

        access_token = result.get(
            "idToken"
        )

        refresh_token = result.get(
            "refreshToken"
        )


    user_id = sync_user_with_database(
        email=firebase_email,
        role=role,
        full_name=result.get("displayName")
    )


    return jsonify({

        "message":
        "Google sign in successful",

        "user_id":
        user_id,

        "uid":
        uid,

        "email":
        firebase_email,

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
# GET ALL USERS
# ONLY MAIN ADMIN
# =========================================================

@auth_bp.route(
    "/users",
    methods=["GET"]
)
@main_admin_required
def get_users():

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
                ID,
                Full_Name,
                Email,
                Role,
                Created_At,
                Updated_At
            FROM `USER`
            ORDER BY ID ASC
            """
        )


        users = cursor.fetchall()


        return jsonify({
            "users": users
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
# CHANGE USER ROLE
# ONLY MAIN ADMIN
# =========================================================

@auth_bp.route(
    "/set-role",
    methods=["PUT"]
)
@main_admin_required
def set_role():

    data = request.get_json() or {}

    email = (
        data.get("email")
        or ""
    ).strip()

    new_role = data.get("role")


    if not email or not new_role:

        return jsonify({
            "message":
            "Email and role are required"
        }), 400


    # Omar's admin role cannot be changed
    if (
        email.lower()
        == MAIN_ADMIN_EMAIL.lower()
    ):

        return jsonify({
            "message":
            "Main admin role cannot be changed"
        }), 403


    # Nobody else can become admin
    allowed_roles = [
        "employee",
        "IT"
    ]


    if new_role not in allowed_roles:

        return jsonify({
            "message":
            "Only employee or IT roles are allowed"
        }), 400


    connection = None
    cursor = None


    try:

        # Firebase user must exist
        user_record = (
            firebase_auth.get_user_by_email(
                email
            )
        )


        # Ensure MySQL user exists
        user_id = sync_user_with_database(
            email=email,
            role=new_role,
            full_name=user_record.display_name
        )


        # Update Firebase
        permissions = ROLE_PERMISSIONS[
            new_role
        ]


        firebase_auth.set_custom_user_claims(
            user_record.uid,
            {
                "role": new_role,
                "permissions": permissions
            }
        )


        # Update MySQL
        connection = get_db_connection()

        cursor = connection.cursor()


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