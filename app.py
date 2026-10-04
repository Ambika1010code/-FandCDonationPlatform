from datetime import datetime
import json
import os
import uuid

from flask import Flask, flash, redirect, render_template, request, session, url_for
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_ROLES = {"donor", "receiver", "admin"}

# =========================================================
# DONATION CATEGORIES
# =========================================================

DONATION_CATEGORIES = {
    "Food": [
        "Cooked Food",
        "Dry Food",
        "Canned Food",
        "Fruits",
        "Vegetables",
        "Rice",
        "Flour",
        "Other Food"
    ],

    "Clothes": [
        "Shirts",
        "Pants",
        "Dresses",
        "Jackets",
        "Sweaters",
        "Shoes",
        "Children's Clothes",
        "Other Clothes"
    ],

    "Accessories": [
        "Bags",
        "Belts",
        "Caps",
        "Scarves",
        "Gloves",
        "School Bags",
        "Wallets",
        "Other Accessories"
    ]
}

VALID_DONATION_TYPES = set(DONATION_CATEGORIES.keys())

STATUS_OPTIONS = [
    "Pending",
    "Approved",
    "Rejected",
    "Completed"
]


# =========================================================
# DATABASE
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def close_db(cursor=None, db=None):
    if cursor:
        cursor.close()
    if db:
        db.close()


# =========================================================
# IMAGE UPLOAD HELPERS
# =========================================================

def allowed_image(filename):
    """Check whether the uploaded file has an allowed image extension."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_images(files):
    """Save uploaded images and return their filenames."""
    saved_files = []

    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_image(file.filename):
            continue

        original_name = secure_filename(file.filename)

        unique_name = f"{uuid.uuid4().hex}_{original_name}"

        file_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(file_path)

        saved_files.append(unique_name)

    return saved_files


def delete_uploaded_images(image_names):
    """Delete uploaded images from the uploads folder."""
    if not image_names:
        return

    if isinstance(image_names, str):
        try:
            image_names = json.loads(image_names)
        except (json.JSONDecodeError, TypeError):
            image_names = [image_names]

    for image_name in image_names:
        if not image_name:
            continue

        file_path = os.path.join(
            UPLOAD_FOLDER,
            os.path.basename(image_name)
        )

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


# =========================================================
# AUTH HELPERS
# =========================================================

def logged_in():
    return "user_id" in session


def role_required(role):
    return logged_in() and session.get("role") == role


def parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def dashboard_for(role):
    if role == "donor":
        return "donor_dashboard"

    if role == "receiver":
        return "receiver_dashboard"

    if role == "admin":
        return "admin_dashboard"

    return "index"


# =========================================================
# COMMON DATA
# =========================================================

@app.context_processor
def common_data():

    stats = {
        "meals": 0,
        "clothes": 0,
        "users": 0,
        "pending": 0,
    }

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Food
        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total "
            "FROM donations WHERE donation_type='Food'"
        )

        stats["meals"] = cursor.fetchone()["total"]

        # Clothes
        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total "
            "FROM donations WHERE donation_type='Clothes'"
        )

        stats["clothes"] = cursor.fetchone()["total"]

        # Users
        cursor.execute(
            "SELECT COUNT(*) AS total "
            "FROM users "
            "WHERE role IN ('donor','receiver')"
        )

        stats["users"] = cursor.fetchone()["total"]

        # Pending donations + requests
        cursor.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM donations WHERE status='Pending') + "
            "(SELECT COUNT(*) FROM donation_requests WHERE status='Pending') "
            "AS total"
        )

        stats["pending"] = cursor.fetchone()["total"]

        close_db(cursor, db)

    except mysql.connector.Error:
        pass

    return {
        "logged_in": logged_in(),
        "current_user": session.get("name"),
        "current_role": session.get("role"),
        "platform_stats": stats,
        "status_options": STATUS_OPTIONS,
        "donation_categories": DONATION_CATEGORIES,
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not subject or not message:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("contact"))

        db = cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO contact_messages
                (name, email, subject, message)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    subject,
                    message
                ),
            )

            db.commit()

            flash(
                "Your message has been sent successfully.",
                "success"
            )

        except mysql.connector.Error:
            flash(
                "Could not save your message. Check the database connection.",
                "danger"
            )

        finally:
            close_db(cursor, db)

        return redirect(url_for("contact"))

    return render_template("contact.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip()

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "danger"
            )
            return redirect(url_for("login"))

        db = cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE email=%s",
                (email,)
            )

            user = cursor.fetchone()

        except mysql.connector.Error:

            flash(
                "Unable to connect to the database.",
                "danger"
            )

            return redirect(url_for("login"))

        finally:
            close_db(cursor, db)

        if user and check_password_hash(
            user["password"],
            password
        ):

            if selected_role and selected_role != user["role"]:

                flash(
                    "The selected account type does not match this account.",
                    "warning"
                )

                return redirect(url_for("login"))

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            flash(
                f"Welcome back, {user['name']}!",
                "success"
            )

            return redirect(
                url_for(dashboard_for(user["role"]))
            )

        flash(
            "Incorrect email or password.",
            "danger"
        )

    return render_template("login.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )
        role = request.form.get("role", "")

        if (
            not name
            or not email
            or not password
            or role not in {"donor", "receiver"}
        ):

            flash(
                "Please fill the required fields and choose a valid role.",
                "danger"
            )

            return redirect(url_for("register"))

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "danger"
            )

            return redirect(url_for("register"))

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(url_for("register"))

        db = cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "SELECT id FROM users WHERE email=%s",
                (email,)
            )

            if cursor.fetchone():

                flash(
                    "This email is already registered.",
                    "warning"
                )

                return redirect(url_for("register"))

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password, role, phone, address)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    phone,
                    address,
                ),
            )

            db.commit()

            flash(
                "Registration successful. You can now log in.",
                "success"
            )

            return redirect(url_for("login"))

        except mysql.connector.Error:

            flash(
                "Registration failed. Please check your database settings.",
                "danger"
            )

        finally:
            close_db(cursor, db)

    return render_template("register.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("index"))


# =========================================================
# DONATION ROUTES
# =========================================================

@app.route("/donate/food")
def donate_food():
    return redirect(
        url_for(
            "donate",
            category="Food"
        )
    )


@app.route("/donate/clothes")
def donate_clothes():

    if not role_required("donor"):

        flash(
            "Please log in as a donor.",
            "warning"
        )

        return redirect(url_for("login"))

    return render_template(
        "donate.html",
        donation_type="Clothes"
    )


@app.route("/donate/accessories")
def donate_accessories():

    if not role_required("donor"):

        flash(
            "Please log in as a donor.",
            "warning"
        )

        return redirect(url_for("login"))

    return render_template(
        "donate.html",
        donation_type="Accessories"
    )


@app.route("/donate", methods=["GET", "POST"])
def donate():

    if not role_required("donor"):

        flash(
            "Please log in as a donor to donate.",
            "warning"
        )

        return redirect(url_for("login"))

    if request.method == "POST":

        item_types = request.form.getlist("item_type[]")
        item_names = request.form.getlist("item_name[]")
        quantities = request.form.getlist("quantity[]")
        sizes = request.form.getlist("size[]")
        conditions = request.form.getlist("condition[]")

        pickup_location = request.form.get(
            "pickup_location",
            ""
        ).strip()

        contact_phone = request.form.get(
            "phone",
            ""
        ).strip()

        available_date = parse_datetime(
            request.form.get(
                "available_date",
                ""
            ).strip()
        )

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not pickup_location:

            flash(
                "Pickup address is required.",
                "danger"
            )

            return redirect(url_for("donate"))

        if not item_names:

            flash(
                "Please add at least one donation item.",
                "danger"
            )

            return redirect(url_for("donate"))

        items = []

        for i in range(len(item_names)):

            item_type = (
                item_types[i]
                if i < len(item_types)
                else ""
            ).strip()

            item_name = (
                item_names[i]
                if i < len(item_names)
                else ""
            ).strip()

            quantity_text = (
                quantities[i]
                if i < len(quantities)
                else ""
            ).strip()

            size = (
                sizes[i]
                if i < len(sizes)
                else ""
            ).strip()

            condition = (
                conditions[i]
                if i < len(conditions)
                else ""
            ).strip()

            try:
                quantity = int(quantity_text)

            except ValueError:
                quantity = 0

            # Allow Food, Clothes and Accessories
            if item_type not in VALID_DONATION_TYPES:

                flash(
                    f"Invalid category for item {i + 1}.",
                    "danger"
                )

                return redirect(url_for("donate"))

            if not item_name:

                flash(
                    f"Please select an item for item {i + 1}.",
                    "danger"
                )

                return redirect(url_for("donate"))

            if quantity <= 0:

                flash(
                    f"Quantity must be greater than 0 for item {i + 1}.",
                    "danger"
                )

                return redirect(url_for("donate"))

            # Size is required only for Clothes
            if item_type == "Clothes" and not size:

                flash(
                    f"Please select a size for clothing item {i + 1}.",
                    "danger"
                )

                return redirect(url_for("donate"))

            if not condition:

                flash(
                    f"Please select condition for item {i + 1}.",
                    "danger"
                )

                return redirect(url_for("donate"))

            items.append(
                {
                    "type": item_type,
                    "name": item_name,
                    "quantity": quantity,
                    "size": (
                        size
                        if item_type == "Clothes"
                        else ""
                    ),
                    "condition": condition
                }
            )

        images = save_uploaded_images(
            request.files.getlist("images")
        )

        donation_types = {
            item["type"]
            for item in items
        }

        # The database accepts one donation type per record.
        # Keep one category per donation submission.
        if len(donation_types) != 1:

            flash(
                "Please submit Food, Clothes and Accessories as separate donations.",
                "danger"
            )

            if images:
                delete_uploaded_images(json.dumps(images))

            return redirect(url_for("donate"))

        donation_type = next(iter(donation_types))

        first_item = items[0]

        total_quantity = sum(
            item["quantity"]
            for item in items
        )

        sizes_used = {
            item["size"]
            for item in items
            if item["size"]
        }

        if len(sizes_used) == 1:

            main_size = list(
                sizes_used
            )[0]

        elif len(sizes_used) > 1:

            main_size = "Mixed"

        else:

            main_size = None

        conditions_used = {
            item["condition"]
            for item in items
        }

        if len(conditions_used) == 1:

            main_condition = list(
                conditions_used
            )[0]

        else:

            main_condition = "Mixed"

        db = cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO donations
                (
                    user_id,
                    donation_type,
                    item_name,
                    quantity,
                    size,
                    items_json,
                    image_paths,
                    description,
                    contact_phone,
                    `condition`,
                    pickup_location,
                    available_date,
                    status
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, 'Pending'
                )
                """,
                (
                    session["user_id"],
                    donation_type,
                    first_item["name"],
                    total_quantity,
                    main_size,
                    json.dumps(items),
                    json.dumps(images),
                    description,
                    contact_phone,
                    main_condition,
                    pickup_location,
                    available_date
                )
            )

            db.commit()

            flash(
                "Your donation was submitted successfully.",
                "success"
            )

            return redirect(
                url_for("history")
            )

        except mysql.connector.Error:

            if images:
                delete_uploaded_images(
                    json.dumps(images)
                )

            flash(
                "Could not save the donation. Please try again.",
                "danger"
            )

        finally:
            close_db(cursor, db)

    return render_template(
        "donate.html",
        donation_type=request.args.get(
            "category",
            "Food"
        )
    )


# =========================================================
# REQUEST ROUTES
# =========================================================

@app.route("/request")
def request_help():

    if not role_required("receiver"):

        flash(
            "Please log in as a recipient to request help.",
            "warning"
        )

        return redirect(url_for("login"))

    return redirect(
        url_for(
            "request_food"
        )
    )


@app.route("/request/food", methods=["GET", "POST"])
def request_food():

    if not role_required("receiver"):

        flash(
            "Please log in as a recipient.",
            "warning"
        )

        return redirect(url_for("login"))

    if request.method == "POST":

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        quantity_text = request.form.get(
            "quantity",
            ""
        ).strip()

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        contact_phone = request.form.get(
            "phone",
            ""
        ).strip()

        people_count_text = request.form.get(
            "people_count",
            ""
        ).strip()

        needed_by = parse_datetime(
            request.form.get(
                "needed_by",
                ""
            ).strip()
        )

        try:
            quantity = int(quantity_text)

        except ValueError:
            quantity = 0

        try:

            people_count = (
                int(people_count_text)
                if people_count_text
                else None
            )

            if (
                people_count is not None
                and people_count <= 0
            ):
                people_count = None

        except ValueError:
            people_count = None

        if (
            not item_name
            or quantity <= 0
            or not reason
            or not address
        ):

            flash(
                "Please complete all required fields with a valid quantity.",
                "danger"
            )

            return redirect(
                url_for("request_food")
            )

        db = cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO donation_requests
                (
                    user_id,
                    request_type,
                    item_name,
                    quantity,
                    reason,
                    address,
                    contact_phone,
                    people_count,
                    needed_by,
                    description,
                    status
                )
                VALUES
                (
                    %s, 'Food', %s, %s, %s, %s,
                    %s, %s, %s, %s, 'Pending'
                )
                """,
                (
                    session["user_id"],
                    item_name,
                    quantity,
                    reason,
                    address,
                    contact_phone,
                    people_count,
                    needed_by,
                    description,
                ),
            )

            db.commit()

            flash(
                "Food request submitted successfully.",
                "success"
            )

            return redirect(
                url_for("history")
            )

        except mysql.connector.Error:

            flash(
                "Could not save the request. Please try again.",
                "danger"
            )

        finally:
            close_db(cursor, db)

    return render_template(
        "request.html",
        request_type="Food"
    )


@app.route("/request/clothes", methods=["GET", "POST"])
def request_clothes():

    if not role_required("receiver"):

        flash(
            "Please log in as a recipient.",
            "warning"
        )

        return redirect(url_for("login"))

    if request.method == "POST":

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        quantity_text = request.form.get(
            "quantity",
            ""
        ).strip()

        size = request.form.get(
            "size",
            ""
        ).strip()

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        contact_phone = request.form.get(
            "phone",
            ""
        ).strip()

        try:
            quantity = int(quantity_text)

        except ValueError:
            quantity = 0

        if (
            not item_name
            or quantity <= 0
            or not size
            or not reason
            or not address
        ):

            flash(
                "Please complete all required fields with a valid quantity.",
                "danger"
            )

            return redirect(
                url_for("request_clothes")
            )

        db = cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO donation_requests
                (
                    user_id,
                    request_type,
                    item_name,
                    quantity,
                    size,
                    reason,
                    address,
                    contact_phone,
                    description,
                    status
                )
                VALUES
                (
                    %s, 'Clothes', %s, %s, %s,
                    %s, %s, %s, %s, 'Pending'
                )
                """,
                (
                    session["user_id"],
                    item_name,
                    quantity,
                    size,
                    reason,
                    address,
                    contact_phone,
                    description,
                ),
            )

            db.commit()

            flash(
                "Clothes request submitted successfully.",
                "success"
            )

            return redirect(
                url_for("history")
            )

        except mysql.connector.Error:

            flash(
                "Could not save the request. Please try again.",
                "danger"
            )

        finally:
            close_db(cursor, db)

    return render_template(
        "request.html",
        request_type="Clothes"
    )


@app.route("/request/accessories", methods=["GET", "POST"])
def request_accessories():

    if not role_required("receiver"):

        flash(
            "Please log in as a recipient.",
            "warning"
        )

        return redirect(url_for("login"))

    if request.method == "POST":

        item_name = request.form.get("item_name", "").strip()
        quantity_text = request.form.get("quantity", "").strip()
        reason = request.form.get("reason", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()
        contact_phone = request.form.get("phone", "").strip()
        people_count_text = request.form.get("people_count", "").strip()
        needed_by = parse_datetime(request.form.get("needed_by", "").strip())

        try:
            quantity = int(quantity_text)
        except ValueError:
            quantity = 0

        try:
            people_count = int(people_count_text) if people_count_text else None
            if people_count is not None and people_count <= 0:
                people_count = None
        except ValueError:
            people_count = None

        if not item_name or quantity <= 0 or not reason or not address:
            flash(
                "Please complete all required fields with a valid quantity.",
                "danger"
            )
            return redirect(url_for("request_accessories"))

        db = cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO donation_requests
                (
                    user_id, request_type, item_name, quantity, reason,
                    address, contact_phone, people_count, needed_by,
                    description, status
                )
                VALUES
                (%s, 'Accessories', %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                """,
                (
                    session["user_id"], item_name, quantity, reason, address,
                    contact_phone, people_count, needed_by, description,
                ),
            )
            db.commit()
            flash("Accessories request submitted successfully.", "success")
            return redirect(url_for("history"))

        except mysql.connector.Error:
            flash(
                "Could not save the request. Please try again.",
                "danger"
            )

        finally:
            close_db(cursor, db)

    return render_template(
        "request.html",
        request_type="Accessories"
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if not logged_in():

        flash(
            "Please log in first.",
            "warning"
        )

        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        if not name:

            flash(
                "Name cannot be empty.",
                "danger"
            )

            return redirect(url_for("profile"))

        db = cursor = None

        try:

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute(
                """
                UPDATE users
                SET name=%s, phone=%s, address=%s
                WHERE id=%s
                """,
                (
                    name,
                    phone,
                    address,
                    session["user_id"]
                ),
            )

            db.commit()

            session["name"] = name

            flash(
                "Profile updated successfully.",
                "success"
            )

        except mysql.connector.Error:

            flash(
                "Could not update your profile.",
                "danger"
            )

        finally:
            close_db(cursor, db)

        return redirect(url_for("profile"))

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE id=%s",
            (session["user_id"],)
        )

        user = cursor.fetchone()

    except mysql.connector.Error:

        flash(
            "Database connection error.",
            "danger"
        )

        return redirect(url_for("index"))

    finally:
        close_db(cursor, db)

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    if not logged_in():

        flash(
            "Please log in first.",
            "warning"
        )

        return redirect(url_for("login"))

    donations = []
    requests_list = []

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        if session["role"] == "donor":

            cursor.execute(
                """
                SELECT *
                FROM donations
                WHERE user_id=%s
                ORDER BY created_at DESC
                """,
                (session["user_id"],),
            )

            donations = cursor.fetchall()

        elif session["role"] == "receiver":

            cursor.execute(
                """
                SELECT *
                FROM donation_requests
                WHERE user_id=%s
                ORDER BY created_at DESC
                """,
                (session["user_id"],),
            )

            requests_list = cursor.fetchall()

    except mysql.connector.Error:

        flash(
            "Could not load your history.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return render_template(
        "history.html",
        donations=donations,
        requests_list=requests_list,
    )


# =========================================================
# DONOR DASHBOARD
# =========================================================

@app.route("/donor/dashboard")
def donor_dashboard():

    if not role_required("donor"):

        flash(
            "Donor access required.",
            "warning"
        )

        return redirect(url_for("login"))

    total = 0
    delivered = 0
    pending = 0
    recent = []

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(status='Completed'), 0) AS delivered,
                COALESCE(SUM(status='Pending'), 0) AS pending
            FROM donations
            WHERE user_id=%s
            """,
            (session["user_id"],),
        )

        stats = cursor.fetchone()

        total = stats["total"]
        delivered = stats["delivered"]
        pending = stats["pending"]

        cursor.execute(
            """
            SELECT *
            FROM donations
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (session["user_id"],),
        )

        recent = cursor.fetchall()

    except mysql.connector.Error:
        pass

    finally:
        close_db(cursor, db)

    return render_template(
        "donor_dashboard.html",
        total=total,
        delivered=delivered,
        pending=pending,
        recent=recent,
    )


# =========================================================
# RECEIVER DASHBOARD
# =========================================================

@app.route("/receiver/dashboard")
def receiver_dashboard():

    if not role_required("receiver"):

        flash(
            "Recipient access required.",
            "warning"
        )

        return redirect(url_for("login"))

    total = 0
    approved = 0
    pending = 0
    recent = []

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(status='Approved'), 0) AS approved,
                COALESCE(SUM(status='Pending'), 0) AS pending
            FROM donation_requests
            WHERE user_id=%s
            """,
            (session["user_id"],),
        )

        stats = cursor.fetchone()

        total = stats["total"]
        approved = stats["approved"]
        pending = stats["pending"]

        cursor.execute(
            """
            SELECT *
            FROM donation_requests
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (session["user_id"],),
        )

        recent = cursor.fetchall()

    except mysql.connector.Error:
        pass

    finally:
        close_db(cursor, db)

    return render_template(
        "receiver_dashboard.html",
        total=total,
        approved=approved,
        pending=pending,
        recent=recent,
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    users_count = 0
    donations_count = 0
    requests_count = 0
    messages_count = 0

    users = []
    donations = []
    requests_list = []
    messages = []

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT COUNT(*) AS total FROM users"
        )

        users_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donations"
        )

        donations_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donation_requests"
        )

        requests_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM contact_messages"
        )

        messages_count = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, name, email, role, phone, created_at
            FROM users
            ORDER BY created_at DESC
            """
        )

        users = cursor.fetchall()

        cursor.execute(
            """
            SELECT donations.*, users.name AS donor_name
            FROM donations
            JOIN users
            ON donations.user_id=users.id
            ORDER BY donations.created_at DESC
            """
        )

        donations = cursor.fetchall()

        cursor.execute(
            """
            SELECT donation_requests.*,
                   users.name AS receiver_name
            FROM donation_requests
            JOIN users
            ON donation_requests.user_id=users.id
            ORDER BY donation_requests.created_at DESC
            """
        )

        requests_list = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM contact_messages
            ORDER BY created_at DESC
            """
        )

        messages = cursor.fetchall()

    except mysql.connector.Error:

        flash(
            "Could not load all admin data.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return render_template(
        "admin_dashboard.html",
        users_count=users_count,
        donations_count=donations_count,
        requests_count=requests_count,
        messages_count=messages_count,
        total_users=users_count,
        total_donations=donations_count,
        total_requests=requests_count,
        total_messages=messages_count,
        pending_donations=sum(1 for d in donations if d.get("status") == "Pending"),
        pending_requests=sum(1 for r in requests_list if r.get("status") == "Pending"),
        users=users,
        donations=donations,
        requests_list=requests_list,
        requests=requests_list,
        messages=messages,
        status_options=STATUS_OPTIONS,
    )


# =========================================================
# ADMIN REPORTS
# =========================================================

@app.route("/admin/reports")
def admin_reports():

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    report = {
        "total_users": 0,
        "total_donations": 0,
        "total_requests": 0,
        "total_quantity": 0,
        "pending": 0,
        "approved": 0,
        "completed": 0,
        "rejected": 0,
        "food_donations": 0,
        "clothes_donations": 0,
    }

    tracking = []
    db = cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT COUNT(*) AS total FROM users "
            "WHERE role IN ('donor','receiver')"
        )
        report["total_users"] = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(quantity), 0) AS quantity "
            "FROM donations"
        )
        row = cursor.fetchone()
        report["total_donations"] = row["total"]
        report["total_quantity"] = row["quantity"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donation_requests"
        )
        report["total_requests"] = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT status, COUNT(*) AS total "
            "FROM donations GROUP BY status"
        )
        for row in cursor.fetchall():
            status = row["status"]
            if status == "Pending":
                report["pending"] += row["total"]
            elif status == "Approved":
                report["approved"] += row["total"]
            elif status == "Completed":
                report["completed"] += row["total"]
            elif status == "Rejected":
                report["rejected"] += row["total"]

        cursor.execute(
            "SELECT status, COUNT(*) AS total "
            "FROM donation_requests GROUP BY status"
        )
        for row in cursor.fetchall():
            status = row["status"]
            if status == "Pending":
                report["pending"] += row["total"]
            elif status == "Approved":
                report["approved"] += row["total"]
            elif status == "Completed":
                report["completed"] += row["total"]
            elif status == "Rejected":
                report["rejected"] += row["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donations "
            "WHERE donation_type='Food'"
        )
        report["food_donations"] = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donations "
            "WHERE donation_type='Clothes'"
        )
        report["clothes_donations"] = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT 'Donation' AS record_type, "
            "users.name AS person_name, "
            "donations.donation_type AS category, "
            "donations.item_name, donations.quantity, "
            "donations.status, donations.created_at "
            "FROM donations JOIN users ON donations.user_id=users.id "
            "ORDER BY donations.created_at DESC LIMIT 50"
        )
        donation_tracking = cursor.fetchall()

        cursor.execute(
            "SELECT 'Request' AS record_type, "
            "users.name AS person_name, "
            "donation_requests.request_type AS category, "
            "donation_requests.item_name, donation_requests.quantity, "
            "donation_requests.status, donation_requests.created_at "
            "FROM donation_requests "
            "JOIN users ON donation_requests.user_id=users.id "
            "ORDER BY donation_requests.created_at DESC LIMIT 50"
        )
        request_tracking = cursor.fetchall()

        tracking = donation_tracking + request_tracking
        tracking.sort(
            key=lambda item: item["created_at"],
            reverse=True
        )
        tracking = tracking[:50]

    except mysql.connector.Error:

        flash(
            "Could not generate admin report.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return render_template(
        "admin_reports.html",
        report=report,
        tracking=tracking,
    )


# =========================================================
# ADMIN STATUS
# =========================================================

@app.route(
    "/admin/status/donation/<int:donation_id>",
    methods=["POST"]
)
def admin_update_donation_status(donation_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    status = request.form.get(
        "status",
        ""
    )

    if status not in STATUS_OPTIONS:

        flash(
            "Invalid donation status.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE donations
            SET status=%s
            WHERE id=%s
            """,
            (
                status,
                donation_id
            ),
        )

        db.commit()

        flash(
            "Donation status updated.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not update donation status.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


@app.route(
    "/admin/status/request/<int:request_id>",
    methods=["POST"]
)
def admin_update_request_status(request_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    status = request.form.get(
        "status",
        ""
    )

    if status not in STATUS_OPTIONS:

        flash(
            "Invalid request status.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE donation_requests
            SET status=%s
            WHERE id=%s
            """,
            (
                status,
                request_id
            ),
        )

        db.commit()

        flash(
            "Request status updated.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not update request status.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN DELETE USER
# =========================================================

@app.route(
    "/admin/delete/user/<int:user_id>",
    methods=["POST"]
)
def admin_delete_user(user_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    if user_id == session["user_id"]:

        flash(
            "You cannot delete your own admin account.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM users
            WHERE id=%s AND role!='admin'
            """,
            (user_id,),
        )

        db.commit()

        flash(
            "User deleted.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not delete user.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN DELETE DONATION
# =========================================================

@app.route(
    "/admin/delete/donation/<int:donation_id>",
    methods=["POST"]
)
def admin_delete_donation(donation_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "DELETE FROM donations WHERE id=%s",
            (donation_id,)
        )

        db.commit()

        flash(
            "Donation deleted.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not delete donation.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN DELETE REQUEST
# =========================================================

@app.route(
    "/admin/delete/request/<int:request_id>",
    methods=["POST"]
)
def admin_delete_request(request_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM donation_requests
            WHERE id=%s
            """,
            (request_id,)
        )

        db.commit()

        flash(
            "Request deleted.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not delete request.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADMIN DELETE MESSAGE
# =========================================================

@app.route(
    "/admin/delete/message/<int:message_id>",
    methods=["POST"]
)
def admin_delete_message(message_id):

    if not role_required("admin"):

        flash(
            "Admin access required.",
            "warning"
        )

        return redirect(url_for("login"))

    db = cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM contact_messages
            WHERE id=%s
            """,
            (message_id,)
        )

        db.commit()

        flash(
            "Message deleted.",
            "success"
        )

    except mysql.connector.Error:

        flash(
            "Could not delete message.",
            "danger"
        )

    finally:
        close_db(cursor, db)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)