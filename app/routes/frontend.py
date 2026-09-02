from flask import Blueprint, render_template, redirect, url_for

frontend_bp=Blueprint("frontend",__name__)

@frontend_bp.route("/")
def home(): return redirect(url_for("frontend.login_page"))

@frontend_bp.route("/login")
def login_page(): return render_template("auth/login.html")

@frontend_bp.route("/signup")
def signup_page(): return render_template("auth/signup.html")

@frontend_bp.route("/forgot-password")
def forgot_page(): return render_template("auth/reset_password.html")

@frontend_bp.route("/dashboard")
def dashboard_page(): return render_template("dashboard/index.html")

@frontend_bp.route("/tickets")
def tickets_page(): return render_template("tickets/index.html")

@frontend_bp.route("/tickets/new")
def new_ticket_page(): return render_template("tickets/create.html")

@frontend_bp.route("/tickets/<int:ticket_id>")
def ticket_detail_page(ticket_id): return render_template("tickets/detail.html",ticket_id=ticket_id)

@frontend_bp.route("/tickets/<int:ticket_id>/edit")
def ticket_edit_page(ticket_id): return render_template("tickets/edit.html",ticket_id=ticket_id)

@frontend_bp.route("/profile")
def profile_page(): return render_template("dashboard/profile.html")
