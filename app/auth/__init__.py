# app/auth/__init__.py
import os, MySQLdb
from datetime import timedelta, datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app as app, abort
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    current_user, login_required
)
from passlib.hash import pbkdf2_sha256

bp = Blueprint("auth", __name__, url_prefix="/auth")

# ───────────────────  Flask‑Login bootstrap  ────────────────────
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def init_auth(app):
    login_manager.init_app(app)

    # Session‑cookie hardening (already mentioned in report)
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        SESSION_COOKIE_SECURE=True,      # only over HTTPS
        SESSION_COOKIE_HTTPONLY=True,    # JS can’t read it
        SESSION_COOKIE_SAMESITE="Lax",   # CSRF mitigation
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
    )

# ───────────────────  DB helpers  ───────────────────────────────
def get_db():
    if not hasattr(app, "db_conn"):
        app.db_conn = MySQLdb.connect(
            host=os.environ["DB_HOST"],
            user=os.environ["DB_USER"],
            passwd=os.environ["DB_PASS"],
            db=os.environ["DB_NAME"],
            charset="utf8mb4",
            autocommit=True
        )
    return app.db_conn

def fetch_user(username):
    """Unifies Cust_User and Admin_User lookup."""
    conn = get_db()
    cur  = conn.cursor(MySQLdb.cursors.DictCursor)
    for table, role in (("Cust_User", "customer"), ("Admin_User", "admin")):
        cur.execute(f"SELECT * FROM {table} WHERE username=%s", (username,))
        row = cur.fetchone()
        if row:
            row["role"] = role
            return row
    return None

# ───────────────────  User object  ──────────────────────────────
class User(UserMixin):
    def __init__(self, record: dict):
        self.id       = record["userId"]
        self.username = record["username"]
        self.role     = record["role"]

    # Optional: expose roles to Jinja
    def is_admin(self):
        return self.role == "admin"

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur  = conn.cursor(MySQLdb.cursors.DictCursor)
    for table, role in (("Cust_User", "customer"), ("Admin_User", "admin")):
        cur.execute(f"SELECT *, %s AS role FROM {table} WHERE userId=%s", (role, user_id))
        row = cur.fetchone()
        if row:
            return User(row)
    return None

# ───────────────────  Role‑based decorator  ─────────────────────
def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return decorated
    return wrapper

# ───────────────────  Routes  ───────────────────────────────────
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        record = fetch_user(username)
        if record and pbkdf2_sha256.verify(password, record["password_hash"]):
            login_user(User(record))
            session.permanent = True          # obey PERMANENT_SESSION_LIFETIME

            # 💾 Audit trail (Login_History)
            cur = get_db().cursor()
            cur.execute(
                "INSERT INTO Login_History(userId, login_time, ip_addr) VALUES(%s,%s,%s)",
                (record["userId"], datetime.utcnow(), request.remote_addr)
            )

            flash("Welcome back!", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials 🤔", "danger")
    return render_template("signin.html")    # reuse existing template

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for("main.home"))

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Validate fields (WTForms) then…
        username = request.form["username"]
        password = pbkdf2_sha256.hash(request.form["password"])
        # default role = customer
        cur = get_db().cursor()
        cur.execute(
            "INSERT INTO Cust_User(username, password_hash) VALUES(%s,%s)",
            (username, password)
        )
        flash("Account created 🎉 – please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("signup.html")

# ───────────────────  Example protected view  ───────────────────
@bp.route("/admin")
@roles_required("admin")
def admin_dashboard():
    return render_template("adminpage.html")
