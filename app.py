from datetime import datetime
import json
import os
import re
import uuid

from flask import Flask, flash, redirect, render_template, request, session, url_for
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
ROLES = {"donor", "receiver", "admin", "volunteer"}
MEMBER_ROLES = {"donor", "receiver"}
STATUS_OPTIONS = ["Pending", "Approved", "Assigned", "Picked Up", "Delivered", "Rejected"]
DELIVERY_STATUS_OPTIONS = ["Assigned", "Picked Up", "Delivered", "Cancelled"]

DONATION_CATEGORIES = {
    "Food": ["Cooked Meals", "Groceries", "Packaged Food", "Fruits & Vegetables", "Rice", "Bread", "Canned Food", "Flour", "Other Food"],
    "Clothes": ["T-Shirts", "Shirts", "Pants", "Dresses", "Jackets", "Sweaters", "Children's Wear", "Winter Clothes", "Shoes", "Mixed Clothes", "Other Clothes"],
    "Accessories": ["Bags", "School Bags", "Books", "Stationery", "Blankets", "Kitchen Items", "Household Items", "Shoes", "Other Accessories"],
}
VALID_TYPES = set(DONATION_CATEGORIES)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def db_conn():
    return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)


def close_db(cursor=None, db=None):
    if cursor:
        cursor.close()
    if db:
        db.close()


def valid_email(email):
    return bool(EMAIL_RE.fullmatch(email or ""))


def strong_password(password):
    return bool(
        password
        and len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[^A-Za-z0-9]", password)
    )


def logged_in():
    return "user_id" in session


def is_member():
    return logged_in() and session.get("role") in MEMBER_ROLES


def role_required(role):
    return logged_in() and session.get("role") == role


def member_required():
    return is_member()


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def dashboard_for(role):
    return {
        "donor": "donor_dashboard",
        "receiver": "donor_dashboard",
        "admin": "admin_dashboard",
        "volunteer": "volunteer_dashboard",
    }.get(role, "login")


def allowed_image(filename):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS)


def save_uploaded_images(files):
    files = [f for f in files if f and f.filename]
    if len(files) > 5:
        raise ValueError("You can upload a maximum of 5 images.")
    saved = []
    for file in files:
        if not allowed_image(file.filename):
            raise ValueError("Only JPG, JPEG, PNG, WEBP and GIF images are allowed.")
        name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file.save(os.path.join(UPLOAD_FOLDER, name))
        saved.append(name)
    return saved


def delete_uploaded_images(raw):
    if not raw:
        return
    try:
        names = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        names = [raw]
    for name in names or []:
        path = os.path.join(UPLOAD_FOLDER, os.path.basename(str(name)))
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.context_processor
def common_data():
    stats = {"meals": 0, "clothes": 0, "accessories": 0, "users": 0, "pending": 0}
    try:
        db = db_conn(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT COALESCE(SUM(quantity),0) total FROM donations WHERE donation_type='Food'")
        stats["meals"] = cur.fetchone()["total"]
        cur.execute("SELECT COALESCE(SUM(quantity),0) total FROM donations WHERE donation_type='Clothes'")
        stats["clothes"] = cur.fetchone()["total"]
        cur.execute("SELECT COALESCE(SUM(quantity),0) total FROM donations WHERE donation_type='Accessories'")
        stats["accessories"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM users WHERE role IN ('donor','receiver')")
        stats["users"] = cur.fetchone()["total"]
        cur.execute("SELECT (SELECT COUNT(*) FROM donations WHERE status='Pending') + (SELECT COUNT(*) FROM donation_requests WHERE status='Pending') total")
        stats["pending"] = cur.fetchone()["total"]
        close_db(cur, db)
    except mysql.connector.Error:
        pass
    return {
    "current_user": session.get("name"),
    "current_role": session.get("role"),
    "logged_in": logged_in(),
    "stats": stats,
    "platform_stats": stats,
    "donation_categories": DONATION_CATEGORIES,
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not valid_email(email) or not subject or not message:
            flash("Please complete the form with a valid email address.", "danger")
            return redirect(url_for("contact"))
        db = cur = None
        try:
            db = db_conn(); cur = db.cursor()
            cur.execute("INSERT INTO contact_messages (name,email,subject,message) VALUES (%s,%s,%s,%s)", (name,email,subject,message))
            db.commit(); flash("Your message has been sent successfully.", "success")
        except mysql.connector.Error:
            flash("Could not save your message. Please try again.", "danger")
        finally:
            close_db(cur, db)
    return render_template("contact.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not valid_email(email) or not password:
            flash("Enter a valid email address and password.", "danger")
            return redirect(url_for("login"))
        db = cur = None
        try:
            db = db_conn(); cur = db.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
        except mysql.connector.Error:
            flash("Database connection failed. Check MySQL and config.py.", "danger")
            return redirect(url_for("login"))
        finally:
            close_db(cur, db)
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session.permanent = bool(request.form.get("remember"))
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for(dashboard_for(user["role"])))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "").strip()
        if not name or not valid_email(email) or role not in ROLES:
            flash("Please complete all required fields and choose a valid account type.", "danger")
            return redirect(url_for("register"))
        if not strong_password(password):
            flash("Password must be at least 8 characters and include uppercase, lowercase, a number and a special character.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        db = cur = None
        try:
            db = db_conn(); cur = db.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                flash("This email is already registered. Use it to log in.", "warning")
                return redirect(url_for("register"))
            cur.execute("INSERT INTO users (name,email,password,role,phone,address) VALUES (%s,%s,%s,%s,%s,%s)", (name,email,generate_password_hash(password),role,phone,address))
            db.commit()
            flash("Registration successful. You can now log in with your email and password.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as exc:
            flash(f"Registration failed: {exc.msg}", "danger")
        finally:
            close_db(cur, db)
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/donate", methods=["GET", "POST"])
def donate():
    if not member_required():
        flash("Please log in as a Donor/Recipient member to donate.", "warning")
        return redirect(url_for("login"))
    if request.method == "POST":
        types = request.form.getlist("item_type[]")
        names = request.form.getlist("item_name[]")
        quantities = request.form.getlist("quantity[]")
        sizes = request.form.getlist("size[]")
        conditions = request.form.getlist("condition[]")
        pickup = request.form.get("pickup_location", "").strip()
        phone = request.form.get("phone", "").strip()
        available = parse_datetime(request.form.get("available_date", "").strip())
        description = request.form.get("description", "").strip()
        if not pickup or not names or len(names) > 20:
            flash("Add a pickup address and at least one donation item.", "danger")
            return redirect(url_for("donate"))
        items = []
        try:
            for i, name in enumerate(names):
                typ = types[i].strip() if i < len(types) else ""
                qty = int(quantities[i]) if i < len(quantities) and quantities[i].isdigit() else 0
                size = sizes[i].strip() if i < len(sizes) else ""
                condition = conditions[i].strip() if i < len(conditions) else ""
                if typ not in VALID_TYPES or not name.strip() or qty <= 0 or not condition:
                    raise ValueError(f"Complete category, item, quantity and condition for item {i+1}.")
                if typ == "Clothes" and size not in {"Small", "Medium", "Large", "XL", "Mixed"}:
                    raise ValueError(f"Select a valid clothing size for item {i+1}.")
                items.append({"type":typ,"name":name.strip(),"quantity":qty,"size":size if typ=="Clothes" else "","condition":condition})
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("donate"))
        images = request.files.getlist("images")
        try:
            image_names = save_uploaded_images(images)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("donate"))
        totals = {"Food":0,"Clothes":0,"Accessories":0}
        for item in items:
            totals[item["type"]] += item["quantity"]
        donation_type = ", ".join(k for k,v in totals.items() if v > 0)
        primary = items[0]
        total_qty = sum(i["quantity"] for i in items)
        db = cur = None
        try:
            db = db_conn(); cur = db.cursor()
            cur.execute("""INSERT INTO donations (user_id,donation_type,item_name,quantity,size,items_json,image_paths,description,contact_phone,`condition`,pickup_location,available_date,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')""", (session["user_id"],donation_type,primary["name"],total_qty,primary["size"],json.dumps(items),json.dumps(image_names),description,phone,primary["condition"],pickup,available))
            db.commit(); flash("Donation submitted successfully and is now pending NGO review.", "success")
            return redirect(url_for("history"))
        except mysql.connector.Error:
            delete_uploaded_images(image_names)
            flash("Could not save the donation. Please check your database.", "danger")
        finally:
            close_db(cur, db)
    return render_template("donate.html")


# Backward-compatible category links all open the same single Donate page.
@app.route("/donate/food")
def donate_food():
    return redirect(url_for("donate"))
@app.route("/donate/clothes")
def donate_clothes():
    return redirect(url_for("donate"))
@app.route("/donate/accessories")
def donate_accessories():
    return redirect(url_for("donate"))


@app.route("/request", methods=["GET", "POST"])
def request_help():
    if not member_required():
        flash("Please log in to make a request.", "warning")
        return redirect(url_for("login"))
    selected_type = request.args.get("type", "Food")
    if selected_type not in VALID_TYPES:
        selected_type = "Food"
    if request.method == "POST":
        selected_type = request.form.get("request_type", "Food")
        item_name = request.form.get("item_name", "").strip()
        quantity_text = request.form.get("quantity", "").strip()
        size = request.form.get("size", "").strip()
        condition = request.form.get("condition", "").strip()
        reason = request.form.get("reason", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        people_text = request.form.get("people_count", "").strip()
        needed_by = parse_datetime(request.form.get("needed_by", "").strip())
        description = request.form.get("description", "").strip()
        try:
            quantity = int(quantity_text)
            people = int(people_text) if people_text else None
        except ValueError:
            quantity = 0; people = None
        if selected_type not in VALID_TYPES or not item_name or quantity <= 0 or not reason or not address:
            flash("Please complete the request fields with a valid quantity.", "danger")
            return redirect(url_for("request_help", type=selected_type))
        if selected_type == "Clothes" and size not in {"Small","Medium","Large","XL","Mixed"}:
            flash("Please select a valid clothing size.", "danger")
            return redirect(url_for("request_help", type=selected_type))
        if selected_type == "Food" and people is not None and people <= 0:
            flash("Number of people must be greater than zero.", "danger")
            return redirect(url_for("request_help", type=selected_type))
        db = cur = None
        try:
            db = db_conn(); cur = db.cursor()
            cur.execute("""INSERT INTO donation_requests (user_id,request_type,item_name,quantity,size,`condition`,reason,address,contact_phone,people_count,needed_by,description,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')""", (session["user_id"],selected_type,item_name,quantity,size if selected_type=="Clothes" else "",condition,reason,address,phone,people,needed_by,description))
            db.commit(); flash(f"{selected_type} request submitted successfully and is now pending NGO review.", "success")
            return redirect(url_for("history"))
        except mysql.connector.Error:
            flash("Could not save the request. Please try again.", "danger")
        finally:
            close_db(cur, db)
    return render_template("request.html", request_type=selected_type)


# Backward-compatible links all use the single Request page.
@app.route("/request/food", methods=["GET","POST"])
def request_food():
    if request.method == "POST":
        return _forward_request_post("Food")
    return redirect(url_for("request_help", type="Food"))
@app.route("/request/clothes", methods=["GET","POST"])
def request_clothes():
    if request.method == "POST":
        return _forward_request_post("Clothes")
    return redirect(url_for("request_help", type="Clothes"))
@app.route("/request/accessories", methods=["GET","POST"])
def request_accessories():
    if request.method == "POST":
        return _forward_request_post("Accessories")
    return redirect(url_for("request_help", type="Accessories"))


def _forward_request_post(kind):
    # Preserve old form links while using the single request handler.
    data = request.form.to_dict(flat=True)
    data["request_type"] = kind
    with app.test_request_context("/request", method="POST", data=data):
        return request_help()


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not logged_in():
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    db = cur = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not valid_email(email):
            flash("Enter a name and valid email.", "danger")
            return redirect(url_for("profile"))
        try:
            db = db_conn(); cur = db.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE email=%s AND id<>%s", (email,session["user_id"]))
            if cur.fetchone():
                flash("That email is already used by another account.", "danger")
                return redirect(url_for("profile"))
            cur.execute("UPDATE users SET name=%s,email=%s,phone=%s,address=%s WHERE id=%s", (name,email,phone,address,session["user_id"]))
            db.commit(); session["name"] = name
            flash("Profile updated successfully.", "success")
        except mysql.connector.Error:
            flash("Could not update profile.", "danger")
        finally:
            close_db(cur, db)
    try:
        db = db_conn(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id,name,email,role,phone,address,created_at FROM users WHERE id=%s", (session["user_id"],))
        user = cur.fetchone()
    except mysql.connector.Error:
        user = None
    finally:
        close_db(cur, db)
    return render_template("profile.html", user=user)


@app.route("/history")
def history():
    if not logged_in():
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    donations=[]; requests_list=[]
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        if session.get("role") == "admin":
            cur.execute("SELECT d.*,u.name donor_name,u.email donor_email FROM donations d JOIN users u ON d.user_id=u.id ORDER BY d.created_at DESC")
        elif session.get("role") == "volunteer":
            cur.execute("SELECT d.*,u.name donor_name FROM donations d JOIN users u ON d.user_id=u.id ORDER BY d.created_at DESC")
        else:
            cur.execute("SELECT * FROM donations WHERE user_id=%s ORDER BY created_at DESC", (session["user_id"],))
        donations=cur.fetchall()
        for d in donations:
            try: d["items"] = json.loads(d.get("items_json") or "[]")
            except (TypeError,json.JSONDecodeError): d["items"]=[]
        if session.get("role") == "admin":
            cur.execute("SELECT r.*,u.name requester_name,u.email requester_email FROM donation_requests r JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC")
        elif session.get("role") == "volunteer":
            cur.execute("SELECT r.*,u.name requester_name FROM donation_requests r JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC")
        else:
            cur.execute("SELECT * FROM donation_requests WHERE user_id=%s ORDER BY created_at DESC", (session["user_id"],))
        requests_list=cur.fetchall()
    except mysql.connector.Error:
        flash("Could not load history.", "danger")
    finally:
        close_db(cur,db)
    return render_template("history.html", donations=donations, requests_list=requests_list)


@app.route("/dashboard")
def dashboard():
    if not logged_in(): return redirect(url_for("login"))
    return redirect(url_for(dashboard_for(session.get("role"))))


@app.route("/member/dashboard")
def member_dashboard():
    if not member_required():
        flash("Member access required.", "warning")
        return redirect(url_for("login"))
    donations=[]; requests_list=[]; stats={"donations":0,"requests":0,"pending":0,"approved":0}
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT * FROM donations WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session["user_id"],)); donations=cur.fetchall()
        cur.execute("SELECT * FROM donation_requests WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session["user_id"],)); requests_list=cur.fetchall()
        cur.execute("SELECT COUNT(*) n FROM donations WHERE user_id=%s", (session["user_id"],)); stats["donations"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests WHERE user_id=%s", (session["user_id"],)); stats["requests"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donations WHERE user_id=%s AND status='Pending'", (session["user_id"],)); stats["pending"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests WHERE user_id=%s AND status='Pending'", (session["user_id"],)); stats["pending"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donations WHERE user_id=%s AND status='Approved'", (session["user_id"],)); stats["approved"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests WHERE user_id=%s AND status='Approved'", (session["user_id"],)); stats["approved"]+=cur.fetchone()["n"]
    except mysql.connector.Error:
        flash("Could not load dashboard data.", "danger")
    finally: close_db(cur,db)
    return render_template("member_dashboard.html", donations=donations, requests_list=requests_list, stats=stats)


@app.route("/donor/dashboard")
def donor_dashboard():
    return redirect(url_for("member_dashboard"))

@app.route("/receiver/dashboard")
def receiver_dashboard():
    return redirect(url_for("member_dashboard"))


@app.route("/admin/dashboard")
def admin_dashboard():
    if not role_required("admin"):
        flash("NGO Admin access required.", "warning")
        return redirect(url_for("login"))
    users=[]; donations=[]; requests_list=[]; messages=[]; volunteers=[]; tasks=[]
    counts={k:0 for k in ["users","donations","requests","messages","volunteers","pending","delivered"]}
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) n FROM users"); counts["users"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donations"); counts["donations"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests"); counts["requests"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM contact_messages"); counts["messages"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM users WHERE role='volunteer'"); counts["volunteers"]=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donations WHERE status='Pending'"); counts["pending"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests WHERE status='Pending'"); counts["pending"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donations WHERE status='Delivered'"); counts["delivered"]+=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM donation_requests WHERE status='Delivered'"); counts["delivered"]+=cur.fetchone()["n"]
        cur.execute("SELECT id,name,email,role,phone,address,created_at FROM users ORDER BY created_at DESC"); users=cur.fetchall()
        cur.execute("SELECT d.*,u.name donor_name,u.email donor_email FROM donations d JOIN users u ON d.user_id=u.id ORDER BY d.created_at DESC"); donations=cur.fetchall()
        for d in donations:
            try: d["items"]=json.loads(d.get("items_json") or "[]")
            except (TypeError,json.JSONDecodeError): d["items"]=[]
        cur.execute("SELECT r.*,u.name requester_name,u.email requester_email FROM donation_requests r JOIN users u ON r.user_id=u.id ORDER BY r.created_at DESC"); requests_list=cur.fetchall()
        cur.execute("SELECT * FROM contact_messages ORDER BY created_at DESC"); messages=cur.fetchall()
        cur.execute("SELECT id,name,email,phone,address FROM users WHERE role='volunteer' ORDER BY name"); volunteers=cur.fetchall()
        cur.execute("""SELECT dt.*,v.name volunteer_name, v.phone volunteer_phone FROM delivery_tasks dt JOIN users v ON dt.volunteer_id=v.id ORDER BY dt.created_at DESC"""); tasks=cur.fetchall()
    except mysql.connector.Error:
        flash("Could not load all admin data.", "danger")
    finally: close_db(cur,db)
    return render_template("admin_dashboard.html", counts=counts, users=users, donations=donations, requests_list=requests_list, messages=messages, volunteers=volunteers, tasks=tasks, status_options=STATUS_OPTIONS)


@app.route("/admin/reports")
def admin_reports():
    if not role_required("admin"):
        flash("NGO Admin access required.", "warning")
        return redirect(url_for("login"))
    report={}
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        queries={
            "users":"SELECT COUNT(*) n FROM users",
            "donations":"SELECT COUNT(*) n FROM donations",
            "requests":"SELECT COUNT(*) n FROM donation_requests",
            "volunteers":"SELECT COUNT(*) n FROM users WHERE role='volunteer'",
            "pending":"SELECT (SELECT COUNT(*) FROM donations WHERE status='Pending')+(SELECT COUNT(*) FROM donation_requests WHERE status='Pending') n",
            "delivered":"SELECT (SELECT COUNT(*) FROM donations WHERE status='Delivered')+(SELECT COUNT(*) FROM donation_requests WHERE status='Delivered') n",
            "food":"SELECT COUNT(*) n FROM donations WHERE donation_type LIKE '%Food%'",
            "clothes":"SELECT COUNT(*) n FROM donations WHERE donation_type LIKE '%Clothes%'",
            "accessories":"SELECT COUNT(*) n FROM donations WHERE donation_type LIKE '%Accessories%'",
        }
        for key,sql in queries.items(): cur.execute(sql); report[key]=cur.fetchone()["n"]
        cur.execute("SELECT status,COUNT(*) total FROM donations GROUP BY status ORDER BY total DESC"); donation_status=cur.fetchall()
        cur.execute("SELECT status,COUNT(*) total FROM donation_requests GROUP BY status ORDER BY total DESC"); request_status=cur.fetchall()
    except mysql.connector.Error:
        donation_status=[]; request_status=[]; flash("Could not load reports.","danger")
    finally: close_db(cur,db)
    return render_template("admin_reports.html", report=report, donation_status=donation_status, request_status=request_status)


@app.route("/admin/status/donation/<int:donation_id>", methods=["POST"])
def update_donation_status(donation_id):
    if not role_required("admin"):
        return redirect(url_for("login"))
    status=request.form.get("status","")
    if status not in STATUS_OPTIONS:
        flash("Invalid donation status.","danger"); return redirect(url_for("admin_dashboard"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(); cur.execute("UPDATE donations SET status=%s WHERE id=%s",(status,donation_id)); db.commit(); flash("Donation status updated.","success")
    except mysql.connector.Error: flash("Could not update donation status.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/status/request/<int:request_id>", methods=["POST"])
def update_request_status(request_id):
    if not role_required("admin"):
        return redirect(url_for("login"))
    status=request.form.get("status","")
    if status not in STATUS_OPTIONS:
        flash("Invalid request status.","danger"); return redirect(url_for("admin_dashboard"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(); cur.execute("UPDATE donation_requests SET status=%s WHERE id=%s",(status,request_id)); db.commit(); flash("Request status updated.","success")
    except mysql.connector.Error: flash("Could not update request status.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/assign/<kind>/<int:item_id>", methods=["POST"])
def admin_assign(kind,item_id):
    if not role_required("admin"):
        return redirect(url_for("login"))
    volunteer_id=request.form.get("volunteer_id","").strip()
    if kind not in {"donation","request"} or not volunteer_id.isdigit():
        flash("Select a volunteer.","danger"); return redirect(url_for("admin_dashboard"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE id=%s AND role='volunteer'",(int(volunteer_id),))
        if not cur.fetchone(): raise ValueError("Invalid volunteer.")
        cur.execute("SELECT id FROM delivery_tasks WHERE task_type=%s AND item_id=%s",(kind,item_id))
        task=cur.fetchone()
        if task:
            cur.execute("UPDATE delivery_tasks SET volunteer_id=%s,status='Assigned' WHERE id=%s",(int(volunteer_id),task["id"]))
        else:
            cur.execute("INSERT INTO delivery_tasks (task_type,item_id,volunteer_id,status) VALUES (%s,%s,%s,'Assigned')",(kind,item_id,int(volunteer_id)))
        table="donations" if kind=="donation" else "donation_requests"
        cur.execute(f"UPDATE {table} SET status='Assigned' WHERE id=%s",(item_id,)); db.commit(); flash("Delivery task assigned to volunteer.","success")
    except (mysql.connector.Error,ValueError) as exc:
        flash(str(exc) if isinstance(exc,ValueError) else "Could not assign volunteer.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/volunteer/dashboard")
def volunteer_dashboard():
    if not role_required("volunteer"):
        flash("Volunteer access required.","warning"); return redirect(url_for("login"))
    tasks=[]; available_donations=[]; available_requests=[]
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT dt.*,CASE WHEN dt.task_type='donation' THEN d.item_name ELSE r.item_name END item_name,CASE WHEN dt.task_type='donation' THEN d.pickup_location ELSE NULL END pickup_address,CASE WHEN dt.task_type='request' THEN r.address ELSE NULL END delivery_address FROM delivery_tasks dt LEFT JOIN donations d ON dt.task_type='donation' AND dt.item_id=d.id LEFT JOIN donation_requests r ON dt.task_type='request' AND dt.item_id=r.id WHERE dt.volunteer_id=%s ORDER BY dt.created_at DESC",(session["user_id"],)); tasks=cur.fetchall()
        cur.execute("SELECT d.id,d.item_name,d.quantity,d.pickup_location,d.available_date,d.status,u.name donor_name FROM donations d JOIN users u ON d.user_id=u.id WHERE d.status='Approved' AND NOT EXISTS (SELECT 1 FROM delivery_tasks t WHERE t.task_type='donation' AND t.item_id=d.id) ORDER BY d.created_at"); available_donations=cur.fetchall()
        cur.execute("SELECT r.id,r.item_name,r.quantity,r.address,r.needed_by,r.status,u.name requester_name FROM donation_requests r JOIN users u ON r.user_id=u.id WHERE r.status='Approved' AND NOT EXISTS (SELECT 1 FROM delivery_tasks t WHERE t.task_type='request' AND t.item_id=r.id) ORDER BY r.created_at"); available_requests=cur.fetchall()
    except mysql.connector.Error:
        flash("Could not load volunteer delivery tasks.","danger")
    finally: close_db(cur,db)
    return render_template("volunteer_dashboard.html", tasks=tasks, available_donations=available_donations, available_requests=available_requests)


@app.route("/volunteer/claim/<kind>/<int:item_id>", methods=["POST"])
def volunteer_claim(kind,item_id):
    if not role_required("volunteer"):
        return redirect(url_for("login"))
    if kind not in {"donation","request"}:
        flash("Invalid delivery task.","danger"); return redirect(url_for("volunteer_dashboard"))
    table="donations" if kind=="donation" else "donation_requests"
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute(f"SELECT id,status FROM {table} WHERE id=%s",(item_id,)); row=cur.fetchone()
        if not row or row["status"] not in {"Approved","Assigned"}: raise ValueError("This item is not ready for delivery.")
        cur.execute("SELECT id FROM delivery_tasks WHERE task_type=%s AND item_id=%s",(kind,item_id))
        if cur.fetchone(): raise ValueError("This delivery task is already assigned.")
        cur.execute("INSERT INTO delivery_tasks (task_type,item_id,volunteer_id,status) VALUES (%s,%s,%s,'Assigned')",(kind,item_id,session["user_id"]))
        cur.execute(f"UPDATE {table} SET status='Assigned' WHERE id=%s",(item_id,)); db.commit(); flash("Delivery task claimed.","success")
    except (mysql.connector.Error,ValueError) as exc:
        flash(str(exc) if isinstance(exc,ValueError) else "Could not claim task.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("volunteer_dashboard"))


@app.route("/volunteer/status/<int:task_id>", methods=["POST"])
def volunteer_status(task_id):
    if not role_required("volunteer"):
        return redirect(url_for("login"))
    status=request.form.get("status","")
    if status not in DELIVERY_STATUS_OPTIONS:
        flash("Invalid delivery status.","danger"); return redirect(url_for("volunteer_dashboard"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True)
        cur.execute("SELECT * FROM delivery_tasks WHERE id=%s AND volunteer_id=%s",(task_id,session["user_id"])); task=cur.fetchone()
        if not task: raise ValueError("Delivery task not found.")
        cur.execute("UPDATE delivery_tasks SET status=%s,picked_up_at=CASE WHEN %s='Picked Up' THEN NOW() ELSE picked_up_at END,delivered_at=CASE WHEN %s='Delivered' THEN NOW() ELSE delivered_at END,notes=%s WHERE id=%s",(status,status,status,request.form.get("notes"," ").strip(),task_id))
        table="donations" if task["task_type"]=="donation" else "donation_requests"
        main_status={"Assigned":"Assigned","Picked Up":"Picked Up","Delivered":"Delivered","Cancelled":"Rejected"}[status]
        cur.execute(f"UPDATE {table} SET status=%s WHERE id=%s",(main_status,task["item_id"])); db.commit(); flash("Delivery status updated.","success")
    except (mysql.connector.Error,ValueError) as exc:
        flash(str(exc) if isinstance(exc,ValueError) else "Could not update delivery status.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("volunteer_dashboard"))


@app.route("/admin/delete/user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not role_required("admin"): return redirect(url_for("login"))
    if user_id == session.get("user_id"):
        flash("You cannot delete your own admin account.","danger"); return redirect(url_for("admin_dashboard"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(); cur.execute("DELETE FROM users WHERE id=%s",(user_id,)); db.commit(); flash("User deleted.","success")
    except mysql.connector.Error: flash("Could not delete user.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/donation/<int:donation_id>", methods=["POST"])
def delete_donation(donation_id):
    if not role_required("admin"): return redirect(url_for("login"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(dictionary=True); cur.execute("SELECT image_paths FROM donations WHERE id=%s",(donation_id,)); row=cur.fetchone(); cur.execute("DELETE FROM donations WHERE id=%s",(donation_id,)); db.commit();
        if row: delete_uploaded_images(row.get("image_paths"))
        flash("Donation deleted.","success")
    except mysql.connector.Error: flash("Could not delete donation.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/request/<int:request_id>", methods=["POST"])
def delete_request(request_id):
    if not role_required("admin"): return redirect(url_for("login"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(); cur.execute("DELETE FROM donation_requests WHERE id=%s",(request_id,)); db.commit(); flash("Request deleted.","success")
    except mysql.connector.Error: flash("Could not delete request.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/message/<int:message_id>", methods=["POST"])
def delete_message(message_id):
    if not role_required("admin"): return redirect(url_for("login"))
    db=cur=None
    try:
        db=db_conn(); cur=db.cursor(); cur.execute("DELETE FROM contact_messages WHERE id=%s",(message_id,)); db.commit(); flash("Message deleted.","success")
    except mysql.connector.Error: flash("Could not delete message.","danger")
    finally: close_db(cur,db)
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
