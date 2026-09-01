import os
import requests
from functools import wraps
from urllib.parse import urlencode
from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth



load_dotenv()

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)

FIREBASE_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")



ROLE_PERMISSIONS = {

    "admin": [
        "create_ticket",
        "view_all_tickets",
        "update_ticket",
        "delete_ticket",
        "assign_ticket",
        "add_comment"
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

def refresh_firebase_token(refresh_token):

    url = (
        "https://securetoken.googleapis.com/v1/"
        f"token?key={FIREBASE_API_KEY}"
    )

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

            g.current_user = decoded_token

        except Exception:

            return jsonify({
                "message": "Invalid or expired token"
            }), 401

        return f(*args, **kwargs)

    return decorated



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



@auth_bp.route("/signup", methods=["POST"])
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

    role = "employee"

    permissions = set_user_permissions(
        uid,
        role
    )

    refreshed = refresh_firebase_token(
        result.get("refreshToken")
    )

    if not refreshed:
        return jsonify({
            "message": "Account created but token refresh failed"
        }), 500

    return jsonify({
        "message": "Account created successfully",
        "uid": uid,
        "email": result.get("email"),
        "role": role,
        "permissions": permissions,

        "access_token": refreshed.get("id_token"),
        "refresh_token": refreshed.get("refresh_token")
    }), 201



    login_url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    )

    login_payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    login_response = requests.post(
        login_url,
        json=login_payload,
        timeout=10
    )

    login_result = login_response.json()


    return jsonify({

        "message": "Account created successfully",

        "uid": uid,

        "email": result.get("email"),

        "role": role,

        "permissions": permissions,

        "idToken": login_result.get("idToken")

    }), 201



@auth_bp.route("/login", methods=["POST"])
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
        f"accounts:signInWithPassword?key={FIREBASE_API_KEY}"
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

    user_record = firebase_auth.get_user(uid)

    claims = user_record.custom_claims or {}

    role = claims.get("role")
    permissions = claims.get("permissions")

    # If user does not have claims yet
    if not role or permissions is None:

        role = "employee"

        permissions = set_user_permissions(
            uid,
            role
        )

        # Need a fresh JWT after adding claims
        refreshed = refresh_firebase_token(
            result.get("refreshToken")
        )

        if not refreshed:
            return jsonify({
                "message": "Login successful but token refresh failed"
            }), 500

        access_token = refreshed.get("id_token")
        refresh_token = refreshed.get("refresh_token")

    else:

        access_token = result.get("idToken")
        refresh_token = result.get("refreshToken")

    return jsonify({
        "message": "Login successful",
        "uid": uid,
        "email": result.get("email"),
        "role": role,
        "permissions": permissions,

        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200



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
        f"accounts:sendOobCode?key={FIREBASE_API_KEY}"
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
        f"accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    )


    post_body = urlencode({
        "id_token": google_id_token,
        "providerId": "google.com"
    })


    payload = {

        "postBody": post_body,

        "requestUri":
        "http://localhost",

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

    user_record = firebase_auth.get_user(uid)
    claims = user_record.custom_claims or {}

    role = claims.get("role")
    permissions = claims.get("permissions")

    # If permissions are not added yet
    if not role or permissions is None:

        role = "employee"

        permissions = set_user_permissions(
            uid,
            role
        )

        # Get a new JWT containing role + permissions
        refreshed = refresh_firebase_token(
            result.get("refreshToken")
        )

        if not refreshed:
            return jsonify({
                "message":
                "Google login successful but token refresh failed"
            }), 500

        access_token = refreshed.get("id_token")
        refresh_token = refreshed.get("refresh_token")

    else:

        access_token = result.get("idToken")
        refresh_token = result.get("refreshToken")

    return jsonify({
        "message": "Google sign in successful",
        "uid": uid,
        "email": result.get("email"),
        "name": result.get("displayName"),
        "role": role,
        "permissions": permissions,
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200



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

        "uid": user.get("uid"),

        "email": user.get("email"),

        "name": user.get("name"),

        "role": user.get(
            "role",
            "employee"
        ),

        "permissions": user.get(
            "permissions",
            []
        ),

        "email_verified": user.get(
            "email_verified",
            False
        )

    }), 200