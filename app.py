from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
import ast  # for safely converting string to list
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)

# Static Train Routes
routes = [
    {"id": 1, "source": "Hyderabad", "destination": "Chennai", "date": "2025-08-01", "time": "06:00 AM", "price": 450, "seats": 80, "image": "train1.jpg"},
    {"id": 2, "source": "Delhi", "destination": "Kolkata", "date": "2025-08-02", "time": "09:00 AM", "price": 650, "seats": 60, "image": "train2.jpg"},
    {"id": 3, "source": "Mumbai", "destination": "Bangalore", "date": "2025-08-03", "time": "10:30 AM", "price": 500, "seats": 100, "image": "train3.jpg"},
]

# Initialize Database
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_name TEXT,
            email TEXT,
            mobile TEXT,
            route_id INTEGER,
            passenger_data TEXT,
            total_price INTEGER,
            booking_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Homepage
@app.route("/")
def home():
    return render_template("index.html")

# Train Routes Page
@app.route("/routes")
def routes_page():
    return render_template("routes.html", routes=routes)

# Booking Page
@app.route("/book/<int:route_id>")
def book(route_id):
    route = next((r for r in routes if r["id"] == route_id), None)
    return render_template("book.html", route=route)

# Confirm Booking and Store in DB
@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    data = request.form
    route_id = int(data["route_id"])
    contact_name = data["contact_name"]
    email = data["email"]
    mobile = data["mobile"]
    num_passengers = int(data["num_passengers"])
    total_price = int(data["total_price"])

    passengers = []
    for i in range(1, num_passengers + 1):
        passengers.append({
            "name": data[f"pname{i}"],
            "age": data[f"page{i}"],
            "gender": data[f"pgender{i}"]
        })

    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (contact_name, email, mobile, route_id, passenger_data, total_price, booking_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (contact_name, email, mobile, route_id, str(passengers), total_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return redirect(url_for("confirmation", contact=contact_name))

# Booking Confirmation Page
@app.route("/confirmation")
def confirmation():
    contact = request.args.get("contact")
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE contact_name = ? ORDER BY id DESC LIMIT 1", (contact,))
    booking = cursor.fetchone()
    conn.close()

    route = next((r for r in routes if r["id"] == booking[4]), None)
    passenger_list = ast.literal_eval(booking[5])

    return render_template("confirmation.html", booking=booking, route=route, passengers=passenger_list)

# View All Bookings
@app.route("/bookings")
def bookings():
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings")
    all_bookings = cursor.fetchall()
    conn.close()
    return render_template("bookings.html", bookings=all_bookings, routes=routes)

# Search & Show Ticket by Name or ID
@app.route("/show_ticket", methods=["GET", "POST"])
def show_ticket():
    if request.method == "POST":
        search = request.form["search"]

        conn = sqlite3.connect("bookings.db")
        cursor = conn.cursor()

        if search.isdigit():
            cursor.execute("SELECT * FROM bookings WHERE id = ?", (int(search),))
        else:
            cursor.execute("SELECT * FROM bookings WHERE contact_name = ? ORDER BY id DESC LIMIT 1", (search,))

        booking = cursor.fetchone()
        conn.close()

        if booking:
            route = next((r for r in routes if r["id"] == booking[4]), None)
            passenger_list = ast.literal_eval(booking[5])
            return render_template("confirmation.html", booking=booking, route=route, passengers=passenger_list)
        else:
            return render_template("show_ticket.html", error="No ticket found. Please check your input.")

    return render_template("show_ticket.html")

# Download Ticket as PDF
@app.route("/download_ticket")
def download_ticket():
    booking_id = request.args.get("booking_id")
    if not booking_id:
        return "Booking ID required", 400

    try:
        actual_id = int(booking_id[1:])  # remove 'T' prefix
    except:
        return "Invalid booking ID", 400

    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (actual_id,))
    booking = cursor.fetchone()
    conn.close()

    if not booking:
        return "Ticket not found", 404

    route = next((r for r in routes if r["id"] == booking[4]), None)
    passengers = ast.literal_eval(booking[5])

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, height - 50, "🎟️ SwiftTrain Ticket")

    y = height - 100
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Booking ID: T{booking[0]:02}")
    y -= 20
    p.drawString(50, y, f"Name: {booking[1]}")
    y -= 20
    p.drawString(50, y, f"Email: {booking[2]}")
    y -= 20
    p.drawString(50, y, f"Mobile: {booking[3]}")
    y -= 20
    p.drawString(50, y, f"Route: {route['source']} → {route['destination']}")
    y -= 20
    p.drawString(50, y, f"Date: {route['date']}  Time: {route['time']}")
    y -= 20
    p.drawString(50, y, f"Total Fare: ₹{booking[6]}")
    y -= 30

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Passenger List:")
    y -= 20
    p.setFont("Helvetica", 12)
    for i, passenger in enumerate(passengers, 1):
        p.drawString(60, y, f"{i}. {passenger['name']}, Age: {passenger['age']}, Gender: {passenger['gender']}")
        y -= 20

    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 50, "Generated by SwiftTrain - Reliable Intercity Booking")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"Ticket_{booking_id}.pdf", mimetype='application/pdf')

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
