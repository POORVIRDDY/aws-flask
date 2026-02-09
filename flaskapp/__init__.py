import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

def create_app():
    # Explicit template folder so Flask finds /var/www/flaskapp/flaskapp/templates
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "change-this-secret"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "users.db")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    def init_db():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            uploaded_filename TEXT,
            uploaded_wordcount INTEGER
        )
        """)
        conn.commit()
        conn.close()

    init_db()

    def get_user(username):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT username, password, firstname, lastname, email, address,
                   uploaded_filename, uploaded_wordcount
            FROM users WHERE username=?
        """, (username,))
        row = c.fetchone()
        conn.close()
        return row

    @app.route("/")
    def home():
        return redirect(url_for("register_page"))

    @app.route("/register", methods=["GET"])
    def register_page():
        return render_template("register.html")

    @app.route("/register", methods=["POST"])
    def register_submit():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        firstname = request.form.get("firstname", "").strip()
        lastname = request.form.get("lastname", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not all([username, password, firstname, lastname, email, address]):
            flash("All fields are required.")
            return redirect(url_for("register_page"))

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (username, password, firstname, lastname, email, address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password, firstname, lastname, email, address))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            flash("Username already exists.")
            return redirect(url_for("register_page"))

        return redirect(url_for("profile", username=username))

    @app.route("/login", methods=["GET"])
    def login_page():
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login_submit():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        row = get_user(username)
        if not row or row[1] != password:
            flash("Invalid username or password.")
            return redirect(url_for("login_page"))

        return redirect(url_for("profile", username=username))

    @app.route("/profile/<username>")
    def profile(username):
        row = get_user(username)
        if not row:
            flash("User not found. Please login.")
            return redirect(url_for("login_page"))

        user = {
            "username": row[0],
            "firstname": row[2],
            "lastname": row[3],
            "email": row[4],
            "address": row[5],
            "uploaded_filename": row[6],
            "uploaded_wordcount": row[7],
        }
        return render_template("profile.html", user=user)

    @app.route("/upload/<username>", methods=["POST"])
    def upload(username):
        row = get_user(username)
        if not row:
            flash("User not found.")
            return redirect(url_for("login_page"))

        f = request.files.get("file")
        if not f or f.filename == "":
            flash("No file selected.")
            return redirect(url_for("profile", username=username))

        stored_name = f"{username}_Limerick.txt"
        save_path = os.path.join(UPLOAD_DIR, stored_name)
        f.save(save_path)

        with open(save_path, "r", encoding="utf-8", errors="ignore") as fp:
            wordcount = len(fp.read().split())

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            UPDATE users SET uploaded_filename=?, uploaded_wordcount=?
            WHERE username=?
        """, (stored_name, wordcount, username))
        conn.commit()
        conn.close()

        return redirect(url_for("profile", username=username))

    @app.route("/download/<username>")
    def download(username):
        row = get_user(username)
        if not row or not row[6]:
            flash("No file uploaded yet.")
            return redirect(url_for("profile", username=username))

        return send_from_directory(UPLOAD_DIR, row[6], as_attachment=True)

    return app

