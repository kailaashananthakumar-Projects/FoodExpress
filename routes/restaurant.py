"""
Restaurant routes: dashboard, menu management, order management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from routes.auth import login_required
from services.database import execute_query
from services.order_service import update_order_status
from werkzeug.security import generate_password_hash
from mysql.connector import Error

restaurant_bp = Blueprint('restaurant', __name__)


@restaurant_bp.route('/dashboard')
@login_required(role='restaurant')
def dashboard():
    restaurant_id = session['user_id']
    restaurant = execute_query(
        "SELECT * FROM restaurants WHERE id = %s", (restaurant_id,), fetch_one=True
    )
    
    # Stats
    stats = execute_query(
        """SELECT
             COUNT(*) as total_orders,
             SUM(CASE WHEN status='delivered' THEN total_amount ELSE 0 END) as revenue,
             COUNT(CASE WHEN status='pending' THEN 1 END) as pending_orders,
             COUNT(CASE WHEN status='preparing' THEN 1 END) as preparing_orders,
             COUNT(CASE WHEN DATE(created_at) = CURDATE() THEN 1 END) as today_orders
           FROM orders WHERE restaurant_id = %s""",
        (restaurant_id,), fetch_one=True
    )
    
    # Active orders
    active_orders = execute_query(
        """SELECT o.*, c.name as customer_name, c.phone as customer_phone,
                  COUNT(oi.id) as item_count
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN order_items oi ON oi.order_id = o.id
           WHERE o.restaurant_id = %s AND o.status NOT IN ('delivered','cancelled')
           GROUP BY o.id ORDER BY o.created_at ASC""",
        (restaurant_id,), fetch=True
    )
    
    # Food items count
    menu_count = execute_query(
        "SELECT COUNT(*) as cnt FROM food_items WHERE restaurant_id = %s", 
        (restaurant_id,), fetch_one=True
    )
    
    return render_template('restaurant_dashboard.html',
                           restaurant=restaurant,
                           stats=stats,
                           active_orders=active_orders or [],
                           menu_count=menu_count)


@restaurant_bp.route('/menu')
@login_required(role='restaurant')
def menu_management():
    restaurant_id = session['user_id']
    food_items = execute_query(
        """SELECT fi.*, c.name as category_name
           FROM food_items fi LEFT JOIN categories c ON fi.category_id = c.id
           WHERE fi.restaurant_id = %s ORDER BY fi.is_available DESC, fi.name""",
        (restaurant_id,), fetch=True
    )
    categories = execute_query(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY name", fetch=True
    )
    return render_template('menu_management.html',
                           food_items=food_items or [],
                           categories=categories or [])


@restaurant_bp.route('/menu/add', methods=['GET', 'POST'])
@login_required(role='restaurant')
def add_food_item():
    categories = execute_query(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY name", fetch=True
    )
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        category_id = request.form.get('category_id') or None
        image_url = request.form.get('image_url', '').strip()
        is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
        spice_level = request.form.get('spice_level', 'mild')
        preparation_time = request.form.get('preparation_time', 20)
        is_available = 1 if request.form.get('is_available') else 0
        
        if not name or not price:
            flash('Name and price are required.', 'danger')
            return render_template('add_edit_food.html', categories=categories, item=None)
        
        try:
            price = float(price)
            if price <= 0:
                raise ValueError()
        except ValueError:
            flash('Invalid price.', 'danger')
            return render_template('add_edit_food.html', categories=categories, item=None)
        
        execute_query(
            """INSERT INTO food_items
               (restaurant_id, category_id, name, description, price,
                image_url, is_vegetarian, spice_level, preparation_time, is_available)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (session['user_id'], category_id, name, description, price,
             image_url or None, is_vegetarian, spice_level, preparation_time, is_available),
            commit=True
        )
        flash(f"'{name}' added to your menu!", 'success')
        return redirect(url_for('restaurant.menu_management'))
    
    return render_template('add_edit_food.html', categories=categories, item=None)


@restaurant_bp.route('/menu/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required(role='restaurant')
def edit_food_item(item_id):
    restaurant_id = session['user_id']
    item = execute_query(
        "SELECT * FROM food_items WHERE id = %s AND restaurant_id = %s",
        (item_id, restaurant_id), fetch_one=True
    )
    if not item:
        flash('Food item not found.', 'danger')
        return redirect(url_for('restaurant.menu_management'))
    
    categories = execute_query(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY name", fetch=True
    )
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        category_id = request.form.get('category_id') or None
        image_url = request.form.get('image_url', '').strip()
        is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
        spice_level = request.form.get('spice_level', 'mild')
        preparation_time = request.form.get('preparation_time', 20)
        is_available = 1 if request.form.get('is_available') else 0
        
        execute_query(
            """UPDATE food_items SET name=%s, description=%s, price=%s,
               category_id=%s, image_url=%s, is_vegetarian=%s,
               spice_level=%s, preparation_time=%s, is_available=%s
               WHERE id=%s AND restaurant_id=%s""",
            (name, description, price, category_id, image_url or None,
             is_vegetarian, spice_level, preparation_time, is_available,
             item_id, restaurant_id),
            commit=True
        )
        flash(f"'{name}' updated successfully!", 'success')
        return redirect(url_for('restaurant.menu_management'))
    
    return render_template('add_edit_food.html', categories=categories, item=item)


@restaurant_bp.route('/menu/delete/<int:item_id>', methods=['POST'])
@login_required(role='restaurant')
def delete_food_item(item_id):
    restaurant_id = session['user_id']
    item = execute_query(
        "SELECT name FROM food_items WHERE id = %s AND restaurant_id = %s",
        (item_id, restaurant_id), fetch_one=True
    )
    if item:
        execute_query(
            "DELETE FROM food_items WHERE id = %s AND restaurant_id = %s",
            (item_id, restaurant_id), commit=True
        )
        flash(f"'{item['name']}' removed from menu.", 'success')
    else:
        flash('Item not found.', 'danger')
    return redirect(url_for('restaurant.menu_management'))


@restaurant_bp.route('/menu/toggle/<int:item_id>', methods=['POST'])
@login_required(role='restaurant')
def toggle_availability(item_id):
    restaurant_id = session['user_id']
    item = execute_query(
        "SELECT id, is_available FROM food_items WHERE id = %s AND restaurant_id = %s",
        (item_id, restaurant_id), fetch_one=True
    )
    if item:
        new_status = 0 if item['is_available'] else 1
        execute_query(
            "UPDATE food_items SET is_available = %s WHERE id = %s",
            (new_status, item_id), commit=True
        )
        return jsonify({'success': True, 'is_available': bool(new_status)})
    return jsonify({'success': False}), 404


@restaurant_bp.route('/orders')
@login_required(role='restaurant')
def orders():
    restaurant_id = session['user_id']
    status_filter = request.args.get('status', '')
    
    query = """SELECT o.*, c.name as customer_name, c.phone as customer_phone
               FROM orders o JOIN customers c ON o.customer_id = c.id
               WHERE o.restaurant_id = %s"""
    params = [restaurant_id]
    if status_filter:
        query += " AND o.status = %s"
        params.append(status_filter)
    query += " ORDER BY o.created_at DESC"
    
    orders_list = execute_query(query, params, fetch=True)
    
    # Get items for each order
    for order in (orders_list or []):
        order['order_items'] = execute_query(
            """SELECT oi.*, fi.name as food_name
               FROM order_items oi JOIN food_items fi ON oi.food_item_id = fi.id
               WHERE oi.order_id = %s""",
            (order['id'],), fetch=True
        )
    
    return render_template('restaurant_orders.html',
                           orders=orders_list or [],
                           status_filter=status_filter)


@restaurant_bp.route('/orders/<int:order_id>/update', methods=['POST'])
@login_required(role='restaurant')
def update_order(order_id):
    # Security: ensure order belongs to this restaurant
    order = execute_query(
        "SELECT id FROM orders WHERE id = %s AND restaurant_id = %s",
        (order_id, session['user_id']), fetch_one=True
    )
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('restaurant.orders'))
    
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    try:
        update_order_status(order_id, new_status, 'restaurant', notes)
        flash(f'Order #{order_id} updated to "{new_status}".', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('restaurant.orders'))
