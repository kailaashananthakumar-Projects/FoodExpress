"""
Customer routes: dashboard, browse restaurants, menu, cart, checkout, orders, tracking.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from routes.auth import login_required
from services.database import execute_query
from services.order_service import place_order, get_order_details, DISCOUNT_THRESHOLD, DISCOUNT_RATE
from mysql.connector import Error
import json

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required(role='customer')
def dashboard():
    customer_id = session['user_id']
    customer = execute_query(
        "SELECT * FROM customers WHERE id = %s", (customer_id,), fetch_one=True
    )
    recent_orders = execute_query(
        """SELECT o.*, r.name as restaurant_name
           FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
           WHERE o.customer_id = %s ORDER BY o.created_at DESC LIMIT 5""",
        (customer_id,), fetch=True
    )
    stats = execute_query(
        """SELECT COUNT(*) as total, SUM(total_amount) as spent
           FROM orders WHERE customer_id = %s AND status != 'cancelled'""",
        (customer_id,), fetch_one=True
    )
    return render_template('customer_dashboard.html',
                           customer=customer,
                           recent_orders=recent_orders or [],
                           stats=stats)


@customer_bp.route('/restaurants')
def restaurants():
    search = request.args.get('search', '').strip()
    cuisine = request.args.get('cuisine', '').strip()
    
    query = "SELECT * FROM restaurants WHERE is_active = 1"
    params = []
    if search:
        query += " AND (name LIKE %s OR cuisine_type LIKE %s OR description LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if cuisine:
        query += " AND cuisine_type = %s"
        params.append(cuisine)
    query += " ORDER BY rating DESC, name ASC"
    
    restaurants_list = execute_query(query, params, fetch=True)
    cuisines = execute_query(
        "SELECT DISTINCT cuisine_type FROM restaurants WHERE is_active = 1 AND cuisine_type IS NOT NULL ORDER BY cuisine_type",
        fetch=True
    )
    categories = execute_query(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY name", fetch=True
    )
    return render_template('restaurants.html',
                           restaurants=restaurants_list or [],
                           cuisines=[c['cuisine_type'] for c in (cuisines or [])],
                           categories=categories or [],
                           search=search,
                           selected_cuisine=cuisine)


@customer_bp.route('/restaurant/<int:restaurant_id>/menu')
def menu(restaurant_id):
    restaurant = execute_query(
        "SELECT * FROM restaurants WHERE id = %s AND is_active = 1",
        (restaurant_id,), fetch_one=True
    )
    if not restaurant:
        flash('Restaurant not found.', 'danger')
        return redirect(url_for('customer.restaurants'))
    
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category', '')
    veg_only = request.args.get('veg', '')
    
    query = """SELECT fi.*, c.name as category_name
               FROM food_items fi
               LEFT JOIN categories c ON fi.category_id = c.id
               WHERE fi.restaurant_id = %s"""
    params = [restaurant_id]
    
    if search:
        query += " AND (fi.name LIKE %s OR fi.description LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])
    if category_id:
        query += " AND fi.category_id = %s"
        params.append(category_id)
    if veg_only:
        query += " AND fi.is_vegetarian = 1"
    query += " ORDER BY fi.is_available DESC, fi.name ASC"
    
    food_items = execute_query(query, params, fetch=True)
    categories = execute_query(
        """SELECT DISTINCT c.* FROM categories c
           JOIN food_items fi ON fi.category_id = c.id
           WHERE fi.restaurant_id = %s AND c.is_active = 1""",
        (restaurant_id,), fetch=True
    )
    
    return render_template('menu.html',
                           restaurant=restaurant,
                           food_items=food_items or [],
                           categories=categories or [],
                           search=search,
                           selected_category=category_id,
                           veg_only=veg_only,
                           discount_threshold=DISCOUNT_THRESHOLD,
                           discount_rate=int(DISCOUNT_RATE * 100))


@customer_bp.route('/cart')
@login_required(role='customer')
def cart():
    cart_data = session.get('cart', {})
    restaurant_id = session.get('cart_restaurant_id')
    cart_items = []
    restaurant = None
    
    if restaurant_id and cart_data:
        restaurant = execute_query(
            "SELECT * FROM restaurants WHERE id = %s", (restaurant_id,), fetch_one=True
        )
        for food_id_str, qty in cart_data.items():
            item = execute_query(
                "SELECT * FROM food_items WHERE id = %s AND is_available = 1",
                (int(food_id_str),), fetch_one=True
            )
            if item:
                item['quantity'] = qty
                item['item_total'] = round(float(item['price']) * qty, 2)
                cart_items.append(item)
    
    subtotal = sum(i['item_total'] for i in cart_items)
    discount = round(subtotal * DISCOUNT_RATE, 2) if subtotal >= DISCOUNT_THRESHOLD else 0.0
    delivery_fee = float(restaurant['delivery_fee']) if restaurant else 30.0
    total = round(subtotal - discount + delivery_fee, 2)
    
    return render_template('cart.html',
                           cart_items=cart_items,
                           restaurant=restaurant,
                           subtotal=round(subtotal, 2),
                           discount=discount,
                           delivery_fee=delivery_fee,
                           total=total,
                           discount_threshold=DISCOUNT_THRESHOLD,
                           discount_rate=int(DISCOUNT_RATE * 100))


@customer_bp.route('/cart/add', methods=['POST'])
@login_required(role='customer')
def add_to_cart():
    data = request.get_json()
    food_item_id = data.get('food_item_id')
    restaurant_id = data.get('restaurant_id')
    quantity = int(data.get('quantity', 1))
    
    # Check if switching restaurant
    current_restaurant = session.get('cart_restaurant_id')
    if current_restaurant and current_restaurant != restaurant_id:
        return jsonify({'success': False,
                        'message': 'Your cart has items from another restaurant. Clear cart first.',
                        'cart_conflict': True}), 400
    
    # Validate item
    item = execute_query(
        "SELECT id, name, price FROM food_items WHERE id = %s AND restaurant_id = %s AND is_available = 1",
        (food_item_id, restaurant_id), fetch_one=True
    )
    if not item:
        return jsonify({'success': False, 'message': 'Item not available.'}), 400
    
    cart = session.get('cart', {})
    key = str(food_item_id)
    cart[key] = cart.get(key, 0) + quantity
    if cart[key] > 10:
        cart[key] = 10  # Max 10 per item
    
    session['cart'] = cart
    session['cart_restaurant_id'] = restaurant_id
    session.modified = True
    
    total_items = sum(cart.values())
    return jsonify({'success': True, 'cart_count': total_items, 'message': f"'{item['name']}' added to cart!"})


@customer_bp.route('/cart/update', methods=['POST'])
@login_required(role='customer')
def update_cart():
    data = request.get_json()
    food_item_id = str(data.get('food_item_id'))
    quantity = int(data.get('quantity', 0))
    
    cart = session.get('cart', {})
    if quantity <= 0:
        cart.pop(food_item_id, None)
    else:
        cart[food_item_id] = min(quantity, 10)
    
    if not cart:
        session.pop('cart_restaurant_id', None)
    
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'cart_count': sum(cart.values())})


@customer_bp.route('/cart/clear', methods=['POST'])
@login_required(role='customer')
def clear_cart():
    session.pop('cart', None)
    session.pop('cart_restaurant_id', None)
    session.modified = True
    return jsonify({'success': True})


@customer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required(role='customer')
def checkout():
    cart = session.get('cart', {})
    restaurant_id = session.get('cart_restaurant_id')
    
    if not cart or not restaurant_id:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('customer.restaurants'))
    
    customer = execute_query(
        "SELECT * FROM customers WHERE id = %s", (session['user_id'],), fetch_one=True
    )
    restaurant = execute_query(
        "SELECT * FROM restaurants WHERE id = %s AND is_active = 1",
        (restaurant_id,), fetch_one=True
    )
    if not restaurant:
        flash('Restaurant is no longer available.', 'danger')
        return redirect(url_for('customer.restaurants'))
    
    if request.method == 'POST':
        delivery_address = request.form.get('delivery_address', '').strip()
        payment_method = request.form.get('payment_method', 'cash_on_delivery')
        special_instructions = request.form.get('special_instructions', '').strip()
        
        if not delivery_address:
            flash('Delivery address is required.', 'danger')
            return redirect(url_for('customer.checkout'))
        
        cart_items = [
            {'food_item_id': int(fid), 'quantity': qty}
            for fid, qty in cart.items()
        ]
        
        try:
            order_id, totals = place_order(
                customer_id=session['user_id'],
                restaurant_id=restaurant_id,
                cart_items=cart_items,
                delivery_address=delivery_address,
                payment_method=payment_method,
                special_instructions=special_instructions
            )
            # Clear cart
            session.pop('cart', None)
            session.pop('cart_restaurant_id', None)
            session.modified = True
            
            flash(f'Order #{order_id} placed successfully! 🎉', 'success')
            return redirect(url_for('customer.order_tracking', order_id=order_id))
        except ValueError as e:
            flash(str(e), 'danger')
        except Error as e:
            flash('Order placement failed. Please try again.', 'danger')
    
    # Build cart preview
    cart_items_preview = []
    for fid, qty in cart.items():
        item = execute_query(
            "SELECT * FROM food_items WHERE id = %s AND is_available = 1",
            (int(fid),), fetch_one=True
        )
        if item:
            item['quantity'] = qty
            item['item_total'] = round(float(item['price']) * qty, 2)
            cart_items_preview.append(item)
    
    subtotal = sum(i['item_total'] for i in cart_items_preview)
    discount = round(subtotal * DISCOUNT_RATE, 2) if subtotal >= DISCOUNT_THRESHOLD else 0.0
    delivery_fee = float(restaurant['delivery_fee'])
    total = round(subtotal - discount + delivery_fee, 2)
    
    return render_template('checkout.html',
                           cart_items=cart_items_preview,
                           restaurant=restaurant,
                           customer=customer,
                           subtotal=round(subtotal, 2),
                           discount=discount,
                           delivery_fee=delivery_fee,
                           total=total,
                           discount_threshold=DISCOUNT_THRESHOLD,
                           discount_rate=int(DISCOUNT_RATE * 100))


@customer_bp.route('/orders')
@login_required(role='customer')
def order_history():
    orders = execute_query(
        """SELECT o.*, r.name as restaurant_name, r.image_url as restaurant_image
           FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
           WHERE o.customer_id = %s ORDER BY o.created_at DESC""",
        (session['user_id'],), fetch=True
    )
    return render_template('order_history.html', orders=orders or [])


@customer_bp.route('/orders/<int:order_id>/track')
@login_required(role='customer')
def order_tracking(order_id):
    # Security: ensure order belongs to this customer
    order_check = execute_query(
        "SELECT id FROM orders WHERE id = %s AND customer_id = %s",
        (order_id, session['user_id']), fetch_one=True
    )
    if not order_check:
        flash('Order not found.', 'danger')
        return redirect(url_for('customer.order_history'))
    
    details = get_order_details(order_id)
    return render_template('order_tracking.html', **details)


@customer_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required(role='customer')
def cancel_order(order_id):
    order = execute_query(
        "SELECT id, status, customer_id FROM orders WHERE id = %s",
        (order_id,), fetch_one=True
    )
    if not order or order['customer_id'] != session['user_id']:
        flash('Order not found.', 'danger')
        return redirect(url_for('customer.order_history'))
    
    if order['status'] not in ('pending',):
        flash('This order cannot be cancelled at this stage.', 'warning')
        return redirect(url_for('customer.order_tracking', order_id=order_id))
    
    from services.order_service import update_order_status
    try:
        update_order_status(order_id, 'cancelled', 'customer', 'Cancelled by customer')
        flash('Order cancelled successfully.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('customer.order_history'))


@customer_bp.route('/orders/<int:order_id>/status')
@login_required(role='customer')
def order_status_api(order_id):
    """AJAX endpoint for live order status."""
    order = execute_query(
        "SELECT status, updated_at FROM orders WHERE id = %s AND customer_id = %s",
        (order_id, session['user_id']), fetch_one=True
    )
    if not order:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'status': order['status'], 'updated_at': str(order['updated_at'])})
