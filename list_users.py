"""
list_users.py - show every login in the database and flag the ones that can never log in.
Run from the project folder:  python list_users.py
"""
import os, mysql.connector
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))
conn = mysql.connector.connect(
    host=os.environ.get("DB_HOST", "localhost"), port=int(os.environ.get("DB_PORT", 3306)),
    user=os.environ.get("DB_USER", "root"), password=os.environ.get("DB_PASSWORD", ""),
    database=os.environ.get("DB_NAME", "food_delivery"))
cur = conn.cursor()
for table in ("admins", "customers", "restaurants", "delivery_agents"):
    cur.execute(f"SELECT id, email, is_active, password_hash FROM {table} ORDER BY id")
    rows = cur.fetchall()
    print(f"\n== {table} ({len(rows)}) ==")
    for id_, email, active, pw in rows:
        ok = pw.startswith(("scrypt:", "pbkdf2:"))
        note = "" if ok else "   <-- BAD PASSWORD (not hashed, cannot log in)"
        if not active: note += "   <-- INACTIVE"
        print(f"  {id_:>3}  {email}{note}")
