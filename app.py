from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from csv_db import read_csv, write_csv, append_csv, generate_id
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ================= INIT ADMIN =================
def create_default_admin():
    users = read_csv("users.csv")

    if not any(u.get("email") == "admin@123" for u in users):
        admin = {
            "id": generate_id(users),
            "first_name": "Admin",
            "last_name": "User",
            "contact": "",
            "email": "admin@123",
            "password": generate_password_hash("password"),
            "role": "admin",
            "created_at": datetime.now().isoformat()
        }
        append_csv("users.csv", admin)
        print("✅ Default admin created")


create_default_admin()


# ================= AUTH =================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ================= HOME =================
@app.route("/")
def home():
    return render_template("login.html")


# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    users = read_csv("users.csv")

    email = request.form["email"]
    password = request.form["password"]

    user = next((u for u in users if u.get("email") == email), None)

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["role"] = user.get("role", "user")
        return redirect(url_for("dashboard"))

    flash("Invalid credentials")
    return redirect(url_for("home"))


# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    users = read_csv("users.csv")

    if any(u.get("email") == request.form["email"] for u in users):
        flash("Email already exists")
        return redirect(url_for("home"))

    new_user = {
        "id": generate_id(users),
        "first_name": request.form["first_name"],
        "last_name": request.form["last_name"],
        "contact": request.form["contact"],
        "email": request.form["email"],
        "password": generate_password_hash(request.form["password"]),
        "role": "user",
        "created_at": datetime.now().isoformat()
    }

    append_csv("users.csv", new_user)

    flash("Registered successfully")
    return redirect(url_for("home"))


# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        role=session.get("role"),
        user_name=session.get("first_name", "User")
    )


# ================= FIX ROUTES =================
@app.route("/trip_type")
@login_required
def trip_type():
    return redirect(url_for("stateorcountry"))


@app.route("/plan_completed")
@login_required
def plan_completed():
    completed_trips = read_csv("completed_trips.csv")
    years = sorted({trip["visit_date"][:4] for trip in completed_trips if trip.get("visit_date")}, reverse=True)
    return render_template("plan_completed.html", years=years)


# ================= API PLACEHOLDERS =================
@app.route("/get_completed_trips")
@login_required
def get_completed_trips():
    import json
    trips = read_csv("completed_trips.csv")
    places = read_csv("places.csv")
    destinations = read_csv("destinations.csv")

    # Build lookups
    place_lookup = {p["id"]: p for p in places}
    dest_lookup = {d["id"]: d["name"] for d in destinations}

    def clean_dict(d):
        # Remove any None keys and ensure all keys are strings
        return {str(k): v for k, v in d.items() if k is not None}

    cleaned_trips = []
    for trip in trips:
        # Support multiple places (comma-separated IDs)
        place_ids = trip.get("place_id", "").split(",") if trip.get("place_id") else []
        trip_places = []
        for pid in place_ids:
            pid = pid.strip()
            if pid and pid in place_lookup:
                place = place_lookup[pid].copy()
                place["destination_name"] = dest_lookup.get(place["destination_id"], "")
                trip_places.append(clean_dict(place))
        trip["places"] = trip_places
        cleaned_trips.append(clean_dict(trip))

    return jsonify(cleaned_trips)


@app.route("/get_trips")
@login_required
def get_trips():
    return jsonify({"trips": []})


@app.route("/create_trip", methods=["POST"])
@login_required
def create_trip():
    return jsonify({"success": True})


@app.route("/delete_trip/<id>")
@login_required
def delete_trip(id):
    return jsonify({"success": True})


# ================= DESTINATIONS =================
@app.route("/stateorcountry")
@login_required
def stateorcountry():
    travel_type = request.args.get("type", "national")
    search = request.args.get("search", "").strip().lower()

    destinations = read_csv("destinations.csv")

    if search:
        filtered = [
            d for d in destinations
            if d.get("type") == travel_type and search in d.get("name", "").lower()
        ]
    else:
        filtered = [
            d for d in destinations
            if d.get("type") == travel_type
        ]

    return render_template(
        "stateorcountry.html",
        destinations=filtered,
        type=travel_type,                # <-- Pass type
        role=session.get("role")         # <-- Pass role
    )


# ================= CREATE DESTINATION =================
@app.route("/create", methods=["POST"])
@login_required
@admin_required
def create_destination():
    destinations = read_csv("destinations.csv")

    image = request.files.get("image")
    filename = ""

    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    new_dest = {
        "id": generate_id(destinations),
        "name": request.form["name"],
        "type": request.args.get("type", "national"),
        "description": request.form["description"],
        "image": filename,
        "created_at": datetime.now().isoformat()
    }

    append_csv("destinations.csv", new_dest)

    flash("Destination created")
    return redirect(url_for("stateorcountry"))


# ================= PLACES =================
def month_to_num(month):
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    try:
        return months.index(month) + 1
    except ValueError:
        return None

@app.route("/places/<destination_id>")
@login_required
def places(destination_id):
    search = request.args.get("search", "").strip().lower()
    month = request.args.get("month", "")
    activities = request.args.getlist("activity")  # <-- get all checked activities

    places = read_csv("places.csv")
    destinations = read_csv("destinations.csv")
    destination = next((d for d in destinations if d["id"] == destination_id), None)

    filtered_places = [
        p for p in places if p.get("destination_id") == destination_id
    ]

    # Search filter
    if search:
        filtered_places = [
            p for p in filtered_places
            if search in p.get("name", "").lower()
        ]

    # Activity filter
    if activities:
        filtered_places = [
            p for p in filtered_places
            if any(activity.lower() in (p.get("things_to_do") or "").lower() for activity in activities)
        ]

    # Month filter
    if month:
        selected_num = month_to_num(month)
        filtered_places = []
        for place in places:
            from_num = month_to_num(place["best_time_from"])
            to_num = month_to_num(place["best_time_to"])
            if from_num and to_num:
                # Handle ranges that wrap around the year (e.g., Nov to Feb)
                if from_num <= to_num:
                    if from_num <= selected_num <= to_num:
                        filtered_places.append(place)
                else:
                    if selected_num >= from_num or selected_num <= to_num:
                        filtered_places.append(place)
        places = filtered_places

    return render_template(
        "places.html",
        destination=destination,
        places=filtered_places,
        role=session.get("role"),
        completed_place_ids=[],  # add your logic if needed
    )


# ================= ADD PLACE =================
@app.route("/add_place/<destination_id>", methods=["POST"])
@login_required
@admin_required
def add_place(destination_id):
    places = read_csv("places.csv")

    image = request.files.get("image")
    filename = ""

    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    new_place = {
        "id": generate_id(places),
        "destination_id": destination_id,
        "name": request.form["name"],
        "district": request.form["district"],
        "description": request.form["description"],
        "map_link": request.form.get("map_link", ""),
        "things_to_do": ", ".join(request.form.getlist("things_to_do")),
        "best_time_from": request.form["best_from"],
        "best_time_to": request.form["best_to"],
        "image": filename,
        "created_at": datetime.now().isoformat()
    }

    append_csv("places.csv", new_place)

    flash("Place added")
    return redirect(url_for("places", destination_id=destination_id))


# ================= DELETE =================
@app.route("/delete_destination/<id>")
@login_required
@admin_required
def delete_destination(id):
    data = read_csv("destinations.csv")
    new_data = [d for d in data if d["id"] != id]

    if new_data:
        write_csv("destinations.csv", new_data, new_data[0].keys())
    else:
        write_csv("destinations.csv", [], [
            "id","name","type","description","image","created_at"
        ])

    return redirect(url_for("stateorcountry"))


@app.route("/delete_place/<place_id>/<destination_id>")
@login_required
@admin_required
def delete_place(place_id, destination_id):
    places = read_csv("places.csv")
    new_places = [p for p in places if p["id"] != place_id]
    if new_places:
        write_csv("places.csv", new_places, new_places[0].keys())
    else:
        write_csv("places.csv", [], [
            "id","destination_id","name","district","description","map_link","image",
            "things_to_do","best_time_from","best_time_to","created_at"
        ])
    flash("Place deleted")
    return redirect(url_for("places", destination_id=destination_id))


# edit place

@app.route("/get_place/<int:place_id>")
@login_required
def get_place(place_id):
    places = read_csv("places.csv")
    place = next((p for p in places if str(p["id"]) == str(place_id)), None)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    return jsonify(place)


@app.route("/edit_place/<place_id>", methods=["POST"])
@login_required
@admin_required
def edit_place(place_id):
    places = read_csv("places.csv")
    place = next((p for p in places if str(p["id"]) == str(place_id)), None)
    if not place:
        return jsonify({"error": "Place not found"}), 404

    # Update fields from form
    place["name"] = request.form["name"]
    place["district"] = request.form["district"]
    place["description"] = request.form["description"]
    place["map_link"] = request.form.get("map_link", "")
    place["things_to_do"] = ", ".join(request.form.getlist("things_to_do"))
    place["best_time_from"] = request.form["best_from"]
    place["best_time_to"] = request.form["best_to"]

    # Handle image update
    image = request.files.get("image")
    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        place["image"] = filename

    # Save changes
    new_places = [p if str(p["id"]) != str(place_id) else place for p in places]
    write_csv("places.csv", new_places, new_places[0].keys())

    flash("Place updated", "success")
    return redirect(url_for("places", destination_id=place["destination_id"]))


@app.route("/completed_trip")
@login_required
@admin_required
def completed_trip():
    places = read_csv("places.csv")
    destinations = read_csv("destinations.csv")
    # Add destination_name to each place for display in the dropdown
    for place in places:
        dest = next((d for d in destinations if d["id"] == place["destination_id"]), None)
        place["destination_name"] = dest["name"] if dest else ""
    return render_template("completed_trip.html", places=places)


@app.route("/gallery")
@login_required
def gallery():
    return render_template("gallery.html")


@app.route("/save_completed_trip", methods=["POST"])
@login_required
@admin_required
def save_completed_trip():
    completed_trips = read_csv("completed_trips.csv")
    data = request.form

    # Handle multiple places
    places = request.form.getlist("places")
    place_id = ",".join(places)

    # Handle experience/description
    description = data.get("experience", "")

    # Handle Google Drive link
    google_drive_link = data.get("google_drive_link", "")

    # Handle budget
    budget = data.get("budget", "")

    # Handle title image upload
    title_image = request.files.get("title_image")
    title_image_filename = ""
    if title_image and title_image.filename:
        title_image_filename = secure_filename(title_image.filename)
        title_image.save(os.path.join(app.config["UPLOAD_FOLDER"], title_image_filename))

    # Handle people met (serialize as JSON string)
    people_count = int(data.get("people_count", 0))
    people = []
    for idx in range(people_count):
        name = data.get(f"people_name_{idx}", "")
        contact = data.get(f"people_contact_{idx}", "")
        email = data.get(f"people_email_{idx}", "")
        image_file = request.files.get(f"people_image_{idx}")
        image_filename = ""
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        if name:
            people.append({
                "name": name,
                "contact": contact,
                "email": email,
                "image": image_filename
            })

    import json
    new_trip = {
        "id": generate_id(completed_trips),
        "title": data.get("title", ""),
        "place_id": place_id,
        "persons": json.dumps(people),
        "visit_date": data.get("visit_date", ""),
        "description": description,
        "images": title_image_filename,
        "budget": budget,
        "google_drive_link": google_drive_link,
        "created_at": datetime.now().isoformat()
    }

    append_csv("completed_trips.csv", new_trip)
    return jsonify({"success": True})



@app.template_filter('format_description')
def format_description(desc):
    if not desc:
        return ''
    # Convert URLs to clickable links
    desc = re.sub(r'(https?://[^\s<]+)', r'<a href="\1" target="_blank">\1</a>', desc)
    # Convert newlines to <br>
    desc = desc.replace('\n', '<br>')
    return Markup(desc)





@app.route("/delete_completed_trip", methods=["POST"])
@login_required
@admin_required
def delete_completed_trip():
    import json
    data = request.get_json()
    trip_id = str(data.get("trip_id"))
    trips = read_csv("completed_trips.csv")
    new_trips = [t for t in trips if t.get("id") != trip_id]
    if new_trips:
        write_csv("completed_trips.csv", new_trips, new_trips[0].keys())
    else:
        # Write only headers if no trips left
        write_csv("completed_trips.csv", [], [
            "id","title","place_id","persons","visit_date","description","images","budget","google_drive_link","created_at"
        ])
    return jsonify({"success": True})


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=False,host="0.0.0.0",port="8000")







