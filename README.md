# 🍕 FoodExpress — Food Delivery Management System

> A full-featured, multi-role web application for managing food delivery operations.  
> Built with **Flask + MySQL** as a college project.

---

## 📋 Features

### 👤 Customer
- Register / Login
- Browse restaurants with search and cuisine filters
- View restaurant menus (filter by category, veg-only, search)
- Add to cart (with multi-restaurant conflict detection)
- Checkout with delivery address and payment method selection
- 10% automatic discount on orders ≥ ₹500
- Live order tracking with auto-refresh every 30 seconds
- Order history & cancel pending orders

### 🍽️ Restaurant Partner
- Login to restaurant dashboard
- View today's stats (orders, revenue, pending)
- Manage menu items (add, edit, delete, toggle availability)
- View and update order status (Confirmed → Preparing → Ready for Pickup)

### 🏍️ Delivery Agent
- Login to delivery dashboard
- View assigned deliveries
- Update delivery status (Picked Up → Out for Delivery → Delivered)
- View delivery history

### 🛡️ Admin
- Full dashboard with revenue chart (last 7 days)
- Manage customers, restaurants, delivery agents
- Add restaurants and agents with auto-hashed passwords
- Assign delivery agents to ready orders
- Manage food categories
- Sales reports (daily / weekly / monthly)

---

## 🛠️ Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Backend     | Python 3.10+, Flask 3.1           |
| Database    | MySQL 8.0 / 9.x                   |
| ORM         | Raw SQL via mysql-connector-python |
| Auth        | Werkzeug password hashing, Flask sessions |
| Frontend    | Jinja2 templates, custom CSS, vanilla JS |
| Charts      | Chart.js 4.4 (admin dashboard)    |
| Icons       | Font Awesome 6.5                  |
| Fonts       | Google Fonts — Poppins            |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- MySQL 8.0 or 9.x running locally
- pip

### Step 1 — Clone / Download
```bash
cd food_delivery_system
```

### Step 2 — Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment
Edit `.env` (already present) to match your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=food_delivery
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1
```

### Step 5 — Initialize & Seed Database
```bash
python setup_db.py
```

This will:
- Create the `food_delivery` database
- Create all tables from `database/schema.sql`
- Insert demo data with properly hashed passwords

### Step 6 — Run the Application
```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## 🔑 Demo Login Credentials

| Role       | Email                       | Password        |
|------------|-----------------------------|-----------------|
| Admin      | admin@foodexpress.com       | Admin@123       |
| Customer   | john@example.com            | Customer@123    |
| Customer   | jane@example.com            | Customer@123    |
| Restaurant | pizza@palace.com            | Restaurant@123  |
| Restaurant | burger@barn.com             | Restaurant@123  |
| Restaurant | spice@garden.com            | Restaurant@123  |
| Agent      | agent1@foodexpress.com      | Agent@123       |
| Agent      | agent2@foodexpress.com      | Agent@123       |

> **Select the correct role** from the login page dropdown before logging in.

---

## 📁 Project Structure

```
food_delivery_system/
│
├── app.py                   # Flask application entry point
├── config.py                # Configuration from environment
├── setup_db.py              # One-shot DB init + seeder
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (DB credentials)
│
├── database/
│   ├── schema.sql           # MySQL table definitions
│   └── seed.sql             # Reference seed (use setup_db.py instead)
│
├── routes/
│   ├── auth.py              # Login, register, logout + login_required decorator
│   ├── customer.py          # Customer: browse, cart, checkout, tracking
│   ├── restaurant.py        # Restaurant: dashboard, menu, orders
│   ├── delivery.py          # Delivery agent: dashboard, status updates
│   └── admin.py             # Admin: dashboard, management, reports
│
├── services/
│   ├── database.py          # MySQL connection pool + execute_query helpers
│   └── order_service.py     # Order placement, status transitions, validation
│
├── templates/               # Jinja2 HTML templates
│   ├── base.html            # Base layout (navbar, footer, flash messages)
│   ├── index.html           # Homepage with hero, categories, restaurants
│   ├── login.html           # Login page (role selection)
│   ├── register.html        # Customer registration
│   ├── restaurants.html     # Restaurant listing with filters
│   ├── menu.html            # Restaurant menu with cart
│   ├── cart.html            # Shopping cart
│   ├── checkout.html        # Order checkout
│   ├── order_tracking.html  # Live order tracking timeline
│   ├── order_history.html   # Customer order history
│   ├── customer_dashboard.html
│   ├── restaurant_dashboard.html
│   ├── restaurant_orders.html
│   ├── menu_management.html
│   ├── add_edit_food.html
│   ├── delivery_dashboard.html
│   ├── delivery_history.html
│   ├── admin_dashboard.html
│   ├── admin_orders.html
│   ├── admin_customers.html
│   ├── admin_restaurants.html
│   ├── admin_agents.html
│   ├── admin_categories.html
│   ├── admin_reports.html
│   ├── about.html
│   └── error.html
│
└── static/
    ├── css/
    │   └── style.css        # Full custom stylesheet
    ├── js/
    │   └── script.js        # Mobile nav, cart, toasts, utilities
    └── images/
        ├── restaurant_placeholder.svg
        └── food_placeholder.svg
```

---

## 🗄️ Database Schema

| Table              | Purpose                                        |
|--------------------|------------------------------------------------|
| `admins`           | Admin accounts                                 |
| `customers`        | Customer accounts                              |
| `restaurants`      | Restaurant accounts & info                     |
| `delivery_agents`  | Delivery agent accounts                        |
| `categories`       | Food categories (Pizza, Burger, etc.)          |
| `food_items`       | Menu items linked to restaurants & categories  |
| `orders`           | Orders with status, totals, payment info       |
| `order_items`      | Line items for each order                      |
| `order_tracking`   | Status history log for each order              |
| `payments`         | Payment records linked to orders               |

---

## 📐 Order Flow

```
Customer places order
        ↓
   [pending]
        ↓  Restaurant confirms
   [confirmed]
        ↓  Restaurant starts cooking
   [preparing]
        ↓  Food packed
   [ready_for_pickup]
        ↓  Admin assigns agent → Agent picks up
   [picked_up]
        ↓
   [out_for_delivery]
        ↓  Delivered to customer
   [delivered]  ← payment marked 'completed', agent stats updated
```

---

## 🔒 Security Features

- All passwords hashed with Werkzeug (PBKDF2-SHA256)
- Role-based access control via `login_required(role=...)` decorator
- Parameterized SQL queries (no raw string interpolation)
- CSRF protection via Flask-WTF / same-site cookie policy
- Session invalidation on logout
- Cart ownership validated server-side before checkout

---

## ⚙️ Health Check

Visit: **http://127.0.0.1:5000/health**  
Returns `{"status": "ok", "db": "Connection successful"}` if everything is running.

---

## 📝 Notes

- This is a **college project** demonstrating full-stack web development.
- The application uses a **MySQL connection pool** (5 connections) for efficiency.
- Images for restaurants/food items are optional (URL-based); placeholders are shown when missing.
- The discount system automatically applies **10% off** on orders ≥ ₹500 — no coupon needed.

---

*© 2024 FoodExpress — Food Delivery Management System*

---

## ✍️ Sign Up (new in this version)

Open **http://127.0.0.1:5000/register** (or click **Sign Up** in the top bar).
Pick who you are, fill the text boxes, and click **Create Account**:

| Sign up as     | Extra fields                          | Lands on                |
|----------------|---------------------------------------|-------------------------|
| Customer       | Delivery address (optional)           | Customer dashboard      |
| Restaurant     | Address, cuisine type, description    | Restaurant dashboard    |
| Delivery Agent | Vehicle type, vehicle number          | Delivery dashboard      |
| Admin          | Admin code (secret)                   | Admin dashboard         |

Passwords are hashed automatically.

**Admin signup** needs the secret *Admin Code* so strangers cannot make themselves admins.
Default code: `FoodAdmin@2026` - change it in `.env` (`ADMIN_SIGNUP_CODE=...`) and share it only with owners.

## 🚚 How delivery agents are assigned
1. Customer places an order.
2. Restaurant: confirmed -> preparing -> **ready for pickup**.
3. **Admin** assigns an agent from the dashboard *or* from the **Orders** page (Agent column dropdown),
   any time while the order is confirmed / preparing / ready for pickup. The agent is then marked busy.
   Re-assigning or cancelling frees the agent again.
4. Agent dashboard shows the delivery; the agent updates picked up -> out for delivery -> **delivered**.
5. The agent becomes available again and their delivery count increases.

## 🛠️ Helper scripts
- `python list_users.py` - lists every login in all 4 tables and flags broken ones.
- `python add_user.py`   - terminal alternative for creating any user (incl. admin).

## ❗ Troubleshooting
- **`No module named 'routes.auth'`** - `routes/auth.py` is missing or in the wrong place.
  Always run `python app.py` from the folder that contains `app.py`, and make sure
  `routes/` contains `__init__.py` and `auth.py`.
- **Cannot connect to database** - set the correct `DB_PASSWORD` in `.env`, make sure the
  MySQL80 service is running, then open http://127.0.0.1:5000/health.
- **Never insert users in MySQL Workbench with a plain password** - the app only accepts hashed passwords.


## 🔧 Fixes in this version
- **Restaurant > Orders page crashed** (so restaurants could never mark orders *ready*, and agents never received deliveries). Fixed.
- **Admin > Reports page crashed.** Fixed.
- Admin can now assign / change the agent on the **Orders** page, not just the dashboard.
- Agents see allotted orders as soon as they are assigned (even while the restaurant is still preparing).
- Pickup / delivery cannot be marked without an assigned agent; cancelling or re-assigning frees the agent.
