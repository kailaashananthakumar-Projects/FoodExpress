"""
Admin routes: dashboard, user management, order management, reports.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from routes.auth import login_required
from services.database import execute_query
from services.order_service import update_order_status
from werkzeug.security import generate_password_hash
from mysql.connector import Error
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required(role='admin')
def dashboard():
    # Key stats
    stats = execute_query(
        """SELECT
             (SELECT COUNT(*) FROM customers WHERE is_active=1) as total_customers,
             (SELECT COUNT(*) FROM restaurants WHERE is_active=1) as total_restaurants,
             (SELECT COUNT(*) FROM delivery_agents WHERE is_active=1) as total_agents,
             (SELECT COUNT(*) FROM orders) as total_orders,
             (SELECT COUNT(*) FROM orders WHERE status='pending') as pending_orders,
             (SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status='delivered') as total_revenue,
             (SELECT COUNT(*) FROM orders WHERE DATE(created_at)=CURDATE()) as today_orders,
             (SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status='delivered' AND DATE(created_at)=CURDATE()) as today_revenue""",
        fetch_one=True
    )
    
    # Recent orders
    recent_orders = execute_query(
        """SELECT o.*, c.name as customer_name, r.name as restaurant_name
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN restaurants r ON o.restaurant_id = r.id
           ORDER BY o.created_at DESC LIMIT 10""",
        fetch=True
    )
    
    # Orders needing agent assignment
    unassigned_orders = execute_query(
        """SELECT o.*, c.name as customer_name, r.name as restaurant_name
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN restaurants r ON o.restaurant_id = r.id
           WHERE o.status IN ('preparing','ready_for_pickup') AND o.delivery_agent_id IS NULL
           ORDER BY o.created_at ASC""",
        fetch=True
    )
    
    available_agents = execute_query(
        "SELECT * FROM delivery_agents WHERE is_active=1 AND is_available=1 ORDER BY name",
        fetch=True
    )
    
    # Revenue chart data - last 7 days
    chart_data = execute_query(
        """SELECT DATE(created_at) as date, 
                  COUNT(*) as order_count,
                  COALESCE(SUM(total_amount),0) as revenue
           FROM orders WHERE status != 'cancelled'
             AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
           GROUP BY DATE(created_at)
           ORDER BY date ASC""",
        fetch=True
    )
    
    return render_template('admin_dashboard.html',
                           stats=stats,
                           recent_orders=recent_orders or [],
                           unassigned_orders=unassigned_orders or [],
                           available_agents=available_agents or [],
                           chart_data=chart_data or [])


@admin_bp.route('/customers')
@login_required(role='admin')
def customers():
    customers_list = execute_query(
        "SELECT * FROM customers ORDER BY created_at DESC", fetch=True
    )
    return render_template('admin_customers.html', customers=customers_list or [])


@admin_bp.route('/customers/<int:customer_id>/toggle', methods=['POST'])
@login_required(role='admin')
def toggle_customer(customer_id):
    customer = execute_query(
        "SELECT id, is_active FROM customers WHERE id = %s", (customer_id,), fetch_one=True
    )
    if customer:
        new_status = 0 if customer['is_active'] else 1
        execute_query(
            "UPDATE customers SET is_active = %s WHERE id = %s",
            (new_status, customer_id), commit=True
        )
        flash(f'Customer {"activated" if new_status else "deactivated"}.', 'success')
    return redirect(url_for('admin.customers'))


@admin_bp.route('/restaurants')
@login_required(role='admin')
def restaurants():
    restaurants_list = execute_query(
        "SELECT * FROM restaurants ORDER BY created_at DESC", fetch=True
    )
    return render_template('admin_restaurants.html', restaurants=restaurants_list or [])


@admin_bp.route('/restaurants/add', methods=['GET', 'POST'])
@login_required(role='admin')
def add_restaurant():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        address = request.form.get('address', '').strip()
        cuisine_type = request.form.get('cuisine_type', '').strip()
        description = request.form.get('description', '').strip()
        delivery_fee = float(request.form.get('delivery_fee', 30))
        image_url = request.form.get('image_url', '').strip()
        
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('admin_add_restaurant.html')
        
        try:
            ph = generate_password_hash(password)
            execute_query(
                """INSERT INTO restaurants
                   (name, email, password_hash, phone, address, cuisine_type, description,
                    delivery_fee, image_url)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, email, ph, phone, address, cuisine_type, description,
                 delivery_fee, image_url or None),
                commit=True
            )
            flash(f"Restaurant '{name}' added!", 'success')
            return redirect(url_for('admin.restaurants'))
        except Error as e:
            if 'Duplicate' in str(e):
                flash('A restaurant with this email already exists.', 'danger')
            else:
                flash('Failed to add restaurant.', 'danger')
    
    return render_template('admin_add_restaurant.html')


@admin_bp.route('/restaurants/<int:restaurant_id>/toggle', methods=['POST'])
@login_required(role='admin')
def toggle_restaurant(restaurant_id):
    r = execute_query(
        "SELECT id, is_active FROM restaurants WHERE id = %s", (restaurant_id,), fetch_one=True
    )
    if r:
        new_status = 0 if r['is_active'] else 1
        execute_query(
            "UPDATE restaurants SET is_active = %s WHERE id = %s",
            (new_status, restaurant_id), commit=True
        )
        flash(f'Restaurant {"activated" if new_status else "deactivated"}.', 'success')
    return redirect(url_for('admin.restaurants'))


@admin_bp.route('/agents')
@login_required(role='admin')
def agents():
    agents_list = execute_query(
        "SELECT * FROM delivery_agents ORDER BY created_at DESC", fetch=True
    )
    return render_template('admin_agents.html', agents=agents_list or [])


@admin_bp.route('/agents/add', methods=['GET', 'POST'])
@login_required(role='admin')
def add_agent():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        vehicle_type = request.form.get('vehicle_type', 'bike')
        vehicle_number = request.form.get('vehicle_number', '').strip()
        
        if not name or not email or not phone or not password:
            flash('All fields are required.', 'danger')
            return render_template('admin_add_agent.html')
        
        try:
            ph = generate_password_hash(password)
            execute_query(
                """INSERT INTO delivery_agents
                   (name, email, phone, password_hash, vehicle_type, vehicle_number)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (name, email, ph, phone, vehicle_type, vehicle_number or None),
                commit=True
            )
            flash(f"Agent '{name}' added!", 'success')
            return redirect(url_for('admin.agents'))
        except Error as e:
            if 'Duplicate' in str(e):
                flash('An agent with this email already exists.', 'danger')
            else:
                flash('Failed to add agent.', 'danger')
    
    return render_template('admin_add_agent.html')


@admin_bp.route('/agents/<int:agent_id>/toggle', methods=['POST'])
@login_required(role='admin')
def toggle_agent(agent_id):
    agent = execute_query(
        "SELECT id, is_active FROM delivery_agents WHERE id = %s", (agent_id,), fetch_one=True
    )
    if agent:
        new_status = 0 if agent['is_active'] else 1
        execute_query(
            "UPDATE delivery_agents SET is_active = %s WHERE id = %s",
            (new_status, agent_id), commit=True
        )
        flash(f'Agent {"activated" if new_status else "deactivated"}.', 'success')
    return redirect(url_for('admin.agents'))


@admin_bp.route('/orders')
@login_required(role='admin')
def orders():
    status_filter = request.args.get('status', '')
    query = """SELECT o.*, c.name as customer_name, r.name as restaurant_name,
                      da.name as agent_name
               FROM orders o
               JOIN customers c ON o.customer_id = c.id
               JOIN restaurants r ON o.restaurant_id = r.id
               LEFT JOIN delivery_agents da ON o.delivery_agent_id = da.id
               WHERE 1=1"""
    params = []
    if status_filter:
        query += " AND o.status = %s"
        params.append(status_filter)
    query += " ORDER BY o.created_at DESC"
    
    orders_list = execute_query(query, params, fetch=True)
    available_agents = execute_query(
        "SELECT id, name FROM delivery_agents WHERE is_active=1 AND is_available=1 ORDER BY name", fetch=True)
    return render_template('admin_orders.html',
                           orders=orders_list or [],
                           available_agents=available_agents or [],
                           status_filter=status_filter)


@admin_bp.route('/orders/<int:order_id>/assign', methods=['POST'])
@login_required(role='admin')
def assign_agent(order_id):
    back = request.form.get('next') or url_for('admin.dashboard')
    if not back.startswith('/') or back.startswith('//'):   # only redirect inside this site
        back = url_for('admin.dashboard')

    agent_id = request.form.get('agent_id', type=int)
    if not agent_id:
        flash('Please select an agent.', 'danger')
        return redirect(back)

    order = execute_query("SELECT id, status, delivery_agent_id FROM orders WHERE id = %s",
                          (order_id,), fetch_one=True)
    agent = execute_query("SELECT id, name, is_active, is_available FROM delivery_agents WHERE id = %s",
                          (agent_id,), fetch_one=True)
    if not order or not agent:
        flash('Order or agent not found.', 'danger')
    elif order['status'] not in ('confirmed', 'preparing', 'ready_for_pickup'):
        flash(f"Order #{order_id} is already '{order['status']}' - an agent can no longer be assigned.", 'danger')
    elif not agent['is_active']:
        flash(f"{agent['name']} is deactivated.", 'danger')
    elif not agent['is_available'] and agent['id'] != order['delivery_agent_id']:
        flash(f"{agent['name']} is busy with another delivery.", 'danger')
    else:
        previous = order['delivery_agent_id']
        execute_query("UPDATE orders SET delivery_agent_id = %s WHERE id = %s", (agent_id, order_id), commit=True)
        execute_query("UPDATE delivery_agents SET is_available = 0 WHERE id = %s", (agent_id,), commit=True)
        if previous and previous != agent_id:      # re-assigned: free the earlier agent
            execute_query("UPDATE delivery_agents SET is_available = 1 WHERE id = %s", (previous,), commit=True)
        flash(f"{agent['name']} assigned to order #{order_id}.", 'success')
    return redirect(back)


@admin_bp.route('/orders/<int:order_id>/update', methods=['POST'])
@login_required(role='admin')
def update_order(order_id):
    new_status = request.form.get('status')
    notes = request.form.get('notes', 'Updated by admin')
    try:
        update_order_status(order_id, new_status, 'admin', notes)
        flash(f'Order #{order_id} status updated.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.orders'))


@admin_bp.route('/categories')
@login_required(role='admin')
def categories():
    cats = execute_query("SELECT * FROM categories ORDER BY name", fetch=True)
    return render_template('admin_categories.html', categories=cats or [])


@admin_bp.route('/categories/add', methods=['POST'])
@login_required(role='admin')
def add_category():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()
    if name:
        try:
            execute_query(
                "INSERT INTO categories (name, description, image_url) VALUES (%s, %s, %s)",
                (name, description, image_url or None), commit=True
            )
            flash(f"Category '{name}' added!", 'success')
        except Error:
            flash('Category already exists or error occurred.', 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@login_required(role='admin')
def delete_category(cat_id):
    execute_query("DELETE FROM categories WHERE id = %s", (cat_id,), commit=True)
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/reports')
@login_required(role='admin')
def reports():
    period = request.args.get('period', 'daily')
    
    if period == 'daily':
        date_group = "DATE(created_at)"
        date_filter = "created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
    elif period == 'weekly':
        date_group = "YEARWEEK(created_at)"
        date_filter = "created_at >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)"
    else:  # monthly
        date_group = "DATE_FORMAT(created_at, '%Y-%m')"
        date_filter = "created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)"
    
    sales_data = execute_query(
        f"""SELECT {date_group} as period,
                   COUNT(*) as order_count,
                   COALESCE(SUM(total_amount),0) as revenue,
                   COALESCE(SUM(discount_amount),0) as discounts_given,
                   COUNT(CASE WHEN status='delivered' THEN 1 END) as delivered_count,
                   COUNT(CASE WHEN status='cancelled' THEN 1 END) as cancelled_count
           FROM orders WHERE {date_filter}
           GROUP BY {date_group}
           ORDER BY period DESC""",
        fetch=True
    )
    
    totals = execute_query(
        """SELECT COUNT(*) as total_orders,
                  COALESCE(SUM(total_amount),0) as total_revenue,
                  COALESCE(AVG(total_amount),0) as avg_order_value,
                  COUNT(CASE WHEN status='delivered' THEN 1 END) as delivered,
                  COUNT(CASE WHEN status='cancelled' THEN 1 END) as cancelled
           FROM orders""",
        fetch_one=True
    )
    
    top_restaurants = execute_query(
        """SELECT r.name, COUNT(o.id) as order_count,
                  COALESCE(SUM(o.total_amount),0) as revenue
           FROM restaurants r LEFT JOIN orders o ON r.id = o.restaurant_id
             AND o.status = 'delivered'
           GROUP BY r.id, r.name ORDER BY revenue DESC LIMIT 5""",
        fetch=True
    )
    
    top_items = execute_query(
        """SELECT fi.name, r.name as restaurant_name,
                  SUM(oi.quantity) as total_sold,
                  SUM(oi.total_price) as revenue
           FROM order_items oi
           JOIN food_items fi ON oi.food_item_id = fi.id
           JOIN restaurants r ON fi.restaurant_id = r.id
           JOIN orders o ON oi.order_id = o.id
           WHERE o.status = 'delivered'
           GROUP BY fi.id, fi.name, r.name
           ORDER BY total_sold DESC LIMIT 10""",
        fetch=True
    )
    
    return render_template('admin_reports.html',
                           sales_data=sales_data or [],
                           totals=totals,
                           top_restaurants=top_restaurants or [],
                           top_items=top_items or [],
                           period=period)
