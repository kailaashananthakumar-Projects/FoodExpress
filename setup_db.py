"""
setup_db.py — One-shot database setup and seeding script.

Usage:
    python setup_db.py

What it does:
  1. Connects to MySQL (reads .env)
  2. Creates the `food_delivery` database if it doesn't exist
  3. Runs database/schema.sql to create all tables
  4. Seeds demo data with proper Werkzeug password hashes

Demo credentials after running:
  Admin      : admin@foodexpress.com      / Admin@123
  Customer 1 : john@example.com           / Customer@123
  Customer 2 : jane@example.com           / Customer@123
  Restaurant : pizza@palace.com           / Restaurant@123
               burger@barn.com            / Restaurant@123
               spice@garden.com           / Restaurant@123
               dragon@palace.com          / Restaurant@123
               sweet@dreams.com           / Restaurant@123
  Agent      : agent1@foodexpress.com     / Agent@123
               agent2@foodexpress.com     / Agent@123
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host'    : os.environ.get('DB_HOST', 'localhost'),
    'port'    : int(os.environ.get('DB_PORT', 3306)),
    'user'    : os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'root'),
    'charset' : 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
}
DB_NAME = os.environ.get('DB_NAME', 'food_delivery')

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_connection(database=None):
    cfg = dict(DB_CONFIG)
    if database:
        cfg['database'] = database
    return mysql.connector.connect(**cfg)

def run_sql_file(cursor, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()
    # Split on semicolons but ignore empty statements
    statements = [s.strip() for s in raw.split(';') if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except Error as e:
            print(f"  [WARN] {e}")

def h(password):
    """Return a Werkzeug password hash."""
    return generate_password_hash(password)

# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FoodExpress — Database Setup & Seeder")
    print("=" * 60)

    # Step 1: Create database if not exists
    print("\n[1/4] Creating database if not exists...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"USE `{DB_NAME}`")
        conn.commit()
        print(f"      Database `{DB_NAME}` ready.")
    except Error as e:
        print(f"[ERROR] Cannot connect to MySQL: {e}")
        print("        Make sure MySQL is running and .env credentials are correct.")
        sys.exit(1)

    # Step 2: Run schema
    print("\n[2/4] Running schema.sql...")
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"[ERROR] schema.sql not found at {schema_path}")
        sys.exit(1)
    run_sql_file(cur, schema_path)
    conn.commit()
    print("      Tables created (or already exist).")

    # Step 3: Seed data
    print("\n[3/4] Seeding demo data...")

    # --- Admin ---
    try:
        cur.execute(
            "INSERT IGNORE INTO admins (name, email, password_hash) VALUES (%s, %s, %s)",
            ('Admin', 'admin@foodexpress.com', h('Admin@123'))
        )
        print("      ✓ Admin inserted.")
    except Error as e:
        print(f"      Admin: {e}")

    # --- Customers ---
    customers = [
        ('John Doe',   'john@example.com', '9000000001', 'Customer@123', '10 Main Street, Bangalore'),
        ('Jane Smith', 'jane@example.com', '9000000002', 'Customer@123', '22 Park Avenue, Bangalore'),
    ]
    for name, email, phone, pwd, addr in customers:
        try:
            cur.execute(
                "INSERT IGNORE INTO customers (name, email, phone, password_hash, address) VALUES (%s,%s,%s,%s,%s)",
                (name, email, phone, h(pwd), addr)
            )
            print(f"      ✓ Customer {email} inserted.")
        except Error as e:
            print(f"      Customer {email}: {e}")

    # --- Categories ---
    categories = [
        ('Pizza',        'Classic Italian pizzas with fresh toppings'),
        ('Burger',       'Juicy burgers and sandwiches'),
        ('Biryani',      'Aromatic rice dishes with spices'),
        ('Chinese',      'Noodles, fried rice and Asian delights'),
        ('South Indian', 'Dosas, idlis, vadas and more'),
        ('Desserts',     'Sweets, cakes and frozen treats'),
        ('Beverages',    'Cold drinks, juices and shakes'),
        ('Sandwich',     'Fresh and filling sandwiches'),
    ]
    for cname, cdesc in categories:
        try:
            cur.execute(
                "INSERT IGNORE INTO categories (name, description) VALUES (%s, %s)",
                (cname, cdesc)
            )
        except Error as e:
            print(f"      Category {cname}: {e}")
    print("      ✓ Categories inserted.")

    # --- Restaurants ---
    restaurants = [
        ('Pizza Palace',   'pizza@palace.com',  '9876543210', 'Restaurant@123',
         '12 MG Road, Bangalore',               'Italian',
         'Authentic wood-fired pizzas baked to perfection. Family recipes since 1990.',
         30.00, 4.5),
        ('Burger Barn',    'burger@barn.com',   '9876543211', 'Restaurant@123',
         '45 Brigade Road, Bangalore',           'American',
         'Gourmet burgers, crispy fries and thick milkshakes.',
         25.00, 4.2),
        ('Spice Garden',   'spice@garden.com',  '9876543212', 'Restaurant@123',
         '78 Jayanagar 4th Block, Bangalore',    'Indian',
         'Authentic South Indian and Biryani cuisine prepared with love.',
         20.00, 4.7),
        ('Dragon Palace',  'dragon@palace.com', '9876543213', 'Restaurant@123',
         '23 Indiranagar, Bangalore',            'Chinese',
         'The best Chinese food in town – noodles, dim sum and more.',
         35.00, 4.3),
        ('Sweet Dreams',   'sweet@dreams.com',  '9876543214', 'Restaurant@123',
         '56 Koramangala, Bangalore',            'Desserts',
         'Heavenly desserts, cakes and ice cream for every occasion.',
         15.00, 4.6),
    ]
    for rname, remail, rphone, rpwd, raddr, rcuisine, rdesc, rfee, rrating in restaurants:
        try:
            cur.execute(
                """INSERT IGNORE INTO restaurants
                   (name, email, password_hash, phone, address, cuisine_type, description, delivery_fee, rating)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (rname, remail, h(rpwd), rphone, raddr, rcuisine, rdesc, rfee, rrating)
            )
            print(f"      ✓ Restaurant {remail} inserted.")
        except Error as e:
            print(f"      Restaurant {remail}: {e}")

    # --- Delivery Agents ---
    agents = [
        ('Ravi Kumar',  'agent1@foodexpress.com', '9111111111', 'Agent@123', 'bike',  'KA-01-AB-1234'),
        ('Suresh Babu', 'agent2@foodexpress.com', '9111111112', 'Agent@123', 'scooter','KA-01-CD-5678'),
    ]
    for aname, aemail, aphone, apwd, avehicle, anum in agents:
        try:
            cur.execute(
                """INSERT IGNORE INTO delivery_agents
                   (name, email, phone, password_hash, vehicle_type, vehicle_number)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (aname, aemail, aphone, h(apwd), avehicle, anum)
            )
            print(f"      ✓ Agent {aemail} inserted.")
        except Error as e:
            print(f"      Agent {aemail}: {e}")

    conn.commit()

    # --- Food Items (fetch restaurant and category IDs first) ---
    print("\n[4/4] Inserting food items...")

    def get_id(table, col, val):
        cur.execute(f"SELECT id FROM {table} WHERE {col} = %s LIMIT 1", (val,))
        row = cur.fetchone()
        return row[0] if row else None

    pizza_id   = get_id('restaurants', 'email', 'pizza@palace.com')
    burger_id  = get_id('restaurants', 'email', 'burger@barn.com')
    spice_id   = get_id('restaurants', 'email', 'spice@garden.com')
    dragon_id  = get_id('restaurants', 'email', 'dragon@palace.com')
    sweet_id   = get_id('restaurants', 'email', 'sweet@dreams.com')

    cat_pizza  = get_id('categories', 'name', 'Pizza')
    cat_burger = get_id('categories', 'name', 'Burger')
    cat_biryani= get_id('categories', 'name', 'Biryani')
    cat_chinese= get_id('categories', 'name', 'Chinese')
    cat_south  = get_id('categories', 'name', 'South Indian')
    cat_dessert= get_id('categories', 'name', 'Desserts')
    cat_bev    = get_id('categories', 'name', 'Beverages')
    cat_sand   = get_id('categories', 'name', 'Sandwich')

    food_items = []

    # Pizza Palace
    if pizza_id:
        food_items += [
            (pizza_id, cat_pizza, 'Margherita Pizza',      'Classic tomato, mozzarella and fresh basil.',        199.00, 0, 'mild',   20),
            (pizza_id, cat_pizza, 'Pepperoni Pizza',       'Loaded with pepperoni and melted cheese.',           249.00, 0, 'mild',   22),
            (pizza_id, cat_pizza, 'Veggie Supreme Pizza',  'Bell peppers, onions, olives and corn.',             229.00, 1, 'mild',   20),
            (pizza_id, cat_pizza, 'Spicy Chicken Pizza',   'Grilled chicken with jalapeños and hot sauce.',      279.00, 0, 'hot',    25),
            (pizza_id, cat_pizza, 'BBQ Paneer Pizza',      'Paneer tikka with smoky BBQ sauce.',                 259.00, 1, 'medium', 22),
            (pizza_id, cat_bev,   'Soft Drink',            'Choice of Coke, Pepsi or Sprite.',                   49.00, 1, 'mild',    5),
        ]

    # Burger Barn
    if burger_id:
        food_items += [
            (burger_id, cat_burger, 'Classic Beef Burger',    'Juicy beef patty with lettuce, tomato and cheese.', 179.00, 0, 'mild',   15),
            (burger_id, cat_burger, 'Crispy Chicken Burger',  'Fried chicken fillet with coleslaw and mayo.',      169.00, 0, 'mild',   12),
            (burger_id, cat_burger, 'Veggie Burger',          'Aloo tikki patty with fresh veggies.',              149.00, 1, 'mild',   10),
            (burger_id, cat_burger, 'Double Smash Burger',    'Double patty, double cheese, double joy.',          229.00, 0, 'medium', 18),
            (burger_id, cat_sand,   'Club Sandwich',          'Triple-decker with chicken, egg and veggies.',      159.00, 0, 'mild',   12),
            (burger_id, cat_bev,    'Thick Milkshake',        'Vanilla, Chocolate or Strawberry.',                  99.00, 1, 'mild',    5),
        ]

    # Spice Garden
    if spice_id:
        food_items += [
            (spice_id, cat_biryani,  'Chicken Biryani',       'Fragrant basmati rice with tender chicken.',        199.00, 0, 'medium',  30),
            (spice_id, cat_biryani,  'Veg Biryani',           'Aromatic rice with mixed vegetables and saffron.',  159.00, 1, 'mild',    25),
            (spice_id, cat_biryani,  'Mutton Biryani',        'Slow-cooked mutton biryani with dum masala.',       249.00, 0, 'hot',     40),
            (spice_id, cat_south,    'Masala Dosa',           'Crispy dosa with spiced potato filling.',           89.00,  1, 'medium',  15),
            (spice_id, cat_south,    'Idli Sambar (3 pcs)',   'Soft steamed idlis with sambar and chutney.',        69.00,  1, 'mild',    10),
            (spice_id, cat_south,    'Medu Vada (2 pcs)',     'Crispy lentil fritters with coconut chutney.',       79.00,  1, 'mild',    10),
        ]

    # Dragon Palace
    if dragon_id:
        food_items += [
            (dragon_id, cat_chinese, 'Veg Fried Rice',        'Wok-tossed rice with fresh vegetables.',            149.00, 1, 'mild',   15),
            (dragon_id, cat_chinese, 'Chicken Fried Rice',    'Wok-tossed rice with chicken and spring onion.',    179.00, 0, 'mild',   15),
            (dragon_id, cat_chinese, 'Hakka Noodles',         'Classic stir-fried noodles with soy sauce.',        149.00, 1, 'medium', 15),
            (dragon_id, cat_chinese, 'Manchurian (Dry)',      'Crispy fried balls in tangy Manchurian sauce.',     169.00, 1, 'hot',    18),
            (dragon_id, cat_chinese, 'Chicken Lollipop',      'Marinated chicken wings in chilli glaze.',          199.00, 0, 'extra_hot', 20),
            (dragon_id, cat_bev,     'Hot & Sour Soup',       'Spicy and sour soup with vegetables.',               99.00, 1, 'hot',    10),
        ]

    # Sweet Dreams
    if sweet_id:
        food_items += [
            (sweet_id, cat_dessert, 'Chocolate Lava Cake',   'Warm cake with flowing chocolate center.',           149.00, 1, 'mild',   20),
            (sweet_id, cat_dessert, 'Gulab Jamun (4 pcs)',   'Soft milk-solid balls soaked in rose sugar syrup.',   89.00, 1, 'mild',   10),
            (sweet_id, cat_dessert, 'Vanilla Ice Cream',     'Creamy vanilla ice cream with chocolate sauce.',      79.00, 1, 'mild',    5),
            (sweet_id, cat_dessert, 'Tiramisu',              'Classic Italian coffee dessert.',                    179.00, 1, 'mild',   15),
            (sweet_id, cat_dessert, 'Brownie Sundae',        'Warm brownie with vanilla ice cream and nuts.',      159.00, 1, 'mild',   12),
            (sweet_id, cat_bev,     'Cold Coffee',           'Chilled blended coffee with cream.',                  99.00, 1, 'mild',    5),
        ]

    fi_sql = """INSERT IGNORE INTO food_items
                (restaurant_id, category_id, name, description, price,
                 is_vegetarian, spice_level, preparation_time, is_available)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)"""

    for fi in food_items:
        try:
            cur.execute(fi_sql, fi)
        except Error as e:
            print(f"      Food item '{fi[2]}': {e}")

    conn.commit()
    print(f"      ✓ {len(food_items)} food items inserted.")
    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  ✅  Setup complete!")
    print("=" * 60)
    print("\n  Demo Login Credentials:")
    print("  ─────────────────────────────────────────────────────")
    print("  Role       Email                        Password")
    print("  ─────────────────────────────────────────────────────")
    print("  Admin      admin@foodexpress.com         Admin@123")
    print("  Customer   john@example.com              Customer@123")
    print("  Customer   jane@example.com              Customer@123")
    print("  Restaurant pizza@palace.com              Restaurant@123")
    print("  Restaurant burger@barn.com               Restaurant@123")
    print("  Restaurant spice@garden.com              Restaurant@123")
    print("  Agent      agent1@foodexpress.com        Agent@123")
    print("  Agent      agent2@foodexpress.com        Agent@123")
    print("  ─────────────────────────────────────────────────────")
    print("\n  Now run:  python app.py")
    print("  Open:     http://127.0.0.1:5000\n")


if __name__ == '__main__':
    main()
