"""
Authentication routes: login, register, logout for all roles.
"""
import os
import hmac
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from services.database import execute_query
from mysql.connector import Error

auth_bp = Blueprint('auth', __name__)


def login_required(role=None):
    """Decorator factory for role-based access control."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if role and session.get('role') != role:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect_by_role()
    
    if request.method == 'POST':
        role = request.form.get('role', 'customer')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')

        user = None
        table_map = {
            'customer': 'customers',
            'restaurant': 'restaurants',
            'agent': 'delivery_agents',
            'admin': 'admins',
        }
        table = table_map.get(role)
        if not table:
            flash('Invalid role selected.', 'danger')
            return render_template('login.html')

        try:
            user = execute_query(
                f"SELECT * FROM {table} WHERE email = %s AND is_active = 1",
                (email,), fetch_one=True
            )
        except Error as e:
            flash('Database error. Please try again.', 'danger')
            return render_template('login.html')

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['role'] = role
            session['name'] = user['name']
            session['email'] = user['email']
            session.permanent = True
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect_by_role()
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


def redirect_by_role():
    role = session.get('role')
    if role == 'customer':
        return redirect(url_for('customer.dashboard'))
    elif role == 'restaurant':
        return redirect(url_for('restaurant.dashboard'))
    elif role == 'agent':
        return redirect(url_for('delivery.dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('index'))


SIGNUP_ROLES = ('customer', 'restaurant', 'agent', 'admin')
# Secret code required to create an Admin account (change it in .env -> ADMIN_SIGNUP_CODE)
ADMIN_SIGNUP_CODE = os.environ.get('ADMIN_SIGNUP_CODE', 'FoodAdmin@2026')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Sign-up page for customers, restaurant partners and delivery agents."""
    if 'user_id' in session:
        return redirect_by_role()

    if request.method == 'POST':
        f = request.form
        role = f.get('role', 'customer')
        name = f.get('name', '').strip()
        email = f.get('email', '').strip().lower()
        phone = f.get('phone', '').strip()
        password = f.get('password', '')
        confirm_password = f.get('confirm_password', '')
        address = f.get('address', '').strip()
        cuisine = f.get('cuisine_type', '').strip()
        vehicle_type = f.get('vehicle_type', 'bike').strip() or 'bike'
        vehicle_number = f.get('vehicle_number', '').strip().upper()
        admin_code = f.get('admin_code', '')

        errors = []
        if role not in SIGNUP_ROLES:
            errors.append('Please choose how you want to sign up.')
        if len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('Enter a valid email address.')
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if phone and not 10 <= len(digits) <= 15:
            errors.append('Phone number must have 10 to 15 digits.')
        if role in ('restaurant', 'agent') and not phone:
            errors.append('Phone number is required for restaurants and delivery agents.')
        if role == 'restaurant' and not address:
            errors.append('Restaurant address is required.')
        if role == 'admin' and not hmac.compare_digest(admin_code.encode(), ADMIN_SIGNUP_CODE.encode()):
            errors.append('Invalid admin code. Ask the system owner for the admin signup code.')
        if role == 'agent' and not vehicle_number:
            errors.append('Vehicle number is required for delivery agents.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('register.html', form_data=f)

        table = {'customer': 'customers', 'restaurant': 'restaurants', 'agent': 'delivery_agents', 'admin': 'admins'}[role]
        try:
            if execute_query(f"SELECT id FROM {table} WHERE email = %s", (email,), fetch_one=True):
                flash('An account with this email already exists for this role. Please log in.', 'danger')
                return render_template('register.html', form_data=f)

            pw_hash = generate_password_hash(password)
            if role == 'customer':
                new_id = execute_query(
                    "INSERT INTO customers (name, email, phone, password_hash, address) VALUES (%s,%s,%s,%s,%s)",
                    (name, email, phone, pw_hash, address), commit=True)
            elif role == 'restaurant':
                new_id = execute_query(
                    """INSERT INTO restaurants (name, email, password_hash, phone, address, cuisine_type, description)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (name, email, pw_hash, phone, address, cuisine or 'Multi-cuisine', f.get('description', '').strip()),
                    commit=True)
            elif role == 'admin':
                new_id = execute_query(
                    "INSERT INTO admins (name, email, password_hash) VALUES (%s,%s,%s)",
                    (name, email, pw_hash), commit=True)
            else:
                new_id = execute_query(
                    """INSERT INTO delivery_agents (name, email, phone, password_hash, vehicle_type, vehicle_number)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (name, email, phone, pw_hash, vehicle_type, vehicle_number), commit=True)
        except Exception as e:
            print(f"[REGISTER ERROR] {type(e).__name__}: {e}")
            flash('Could not create the account because of a database problem. Check the terminal for [REGISTER ERROR].', 'danger')
            return render_template('register.html', form_data=f)

        session.clear()
        session['user_id'] = new_id
        session['role'] = role
        session['name'] = name
        session['email'] = email
        session.permanent = True
        flash(f'Account created successfully! Welcome to FoodExpress, {name}!', 'success')
        return redirect_by_role()

    return render_template('register.html', form_data={})


@auth_bp.route('/logout')
def logout():
    name = session.get('name', 'User')
    session.clear()
    flash(f'Goodbye, {name}! You have been logged out.', 'info')
    return redirect(url_for('index'))
