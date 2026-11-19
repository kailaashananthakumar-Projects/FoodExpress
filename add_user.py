"""
add_user.py - create a login manually (any role) with a correctly hashed password.
Run from the project folder:  python add_user.py
"""
import os, getpass, mysql.connector
from dotenv import load_dotenv, find_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(find_dotenv(usecwd=True))
conn = mysql.connector.connect(
    host=os.environ.get("DB_HOST", "localhost"), port=int(os.environ.get("DB_PORT", 3306)),
    user=os.environ.get("DB_USER", "root"), password=os.environ.get("DB_PASSWORD", ""),
    database=os.environ.get("DB_NAME", "food_delivery"))
cur = conn.cursor()

role = input("Role (customer / admin / agent / restaurant): ").strip().lower()
name = input("Full name: ").strip()
email = input("Email: ").strip().lower()
phone = input("Phone: ").strip()
password = getpass.getpass("Password (min 6 chars, hidden while typing): ")
if len(password) < 6:
    raise SystemExit("Password must be at least 6 characters.")
pw = generate_password_hash(password)   # the app only accepts hashed passwords

try:
    if role == "customer":
        cur.execute("INSERT INTO customers (name,email,phone,password_hash,address) VALUES (%s,%s,%s,%s,%s)",
                    (name, email, phone, pw, input("Address (optional): ")))
    elif role == "admin":
        cur.execute("INSERT INTO admins (name,email,password_hash) VALUES (%s,%s,%s)", (name, email, pw))
    elif role == "agent":
        cur.execute("INSERT INTO delivery_agents (name,email,phone,password_hash,vehicle_type,vehicle_number) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (name, email, phone or "0000000000", pw, "bike", input("Vehicle number: ")))
    elif role == "restaurant":
        cur.execute("INSERT INTO restaurants (name,email,password_hash,phone,address,cuisine_type) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (name, email, pw, phone, input("Address: "), input("Cuisine type: ")))
    else:
        raise SystemExit("Unknown role.")
    conn.commit()
    print(f"\nDone. Log in at /login with role '{role}' and email {email}")
except mysql.connector.Error as e:
    print("\nFailed:", e)
