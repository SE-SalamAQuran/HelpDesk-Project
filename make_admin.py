from app import create_app
from app.routes.auth import sync_user_with_database, set_user_permissions
from firebase_admin import auth

EMAIL = "omar.qaisi735@gmail.com"

app = create_app()

with app.app_context():

    user = auth.get_user_by_email(EMAIL)

    user_id = sync_user_with_database(
        email=EMAIL,
        role="admin",
        full_name=user.display_name
    )

    permissions = set_user_permissions(
        user.uid,
        "admin"
    )

    print("Admin created successfully")
    print("Email:", EMAIL)
    print("User ID:", user_id)
    print("Role: admin")
    print("Permissions:", permissions)