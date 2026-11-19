"""
Order Service - Handles all order-related business logic.
Validates prices from DB, applies discounts, manages status transitions.
"""
from services.database import execute_query, execute_transaction
from mysql.connector import Error

# Valid status transitions (current -> allowed_next)
STATUS_TRANSITIONS = {
    'pending':          ['confirmed', 'cancelled'],
    'confirmed':        ['preparing', 'cancelled'],
    'preparing':        ['ready_for_pickup', 'cancelled'],
    'ready_for_pickup': ['picked_up'],
    'picked_up':        ['out_for_delivery'],
    'out_for_delivery': ['delivered'],
    'delivered':        [],
    'cancelled':        [],
}

# Who can perform which transitions
ROLE_ALLOWED_TRANSITIONS = {
    'restaurant': ['confirmed', 'preparing', 'ready_for_pickup', 'cancelled'],
    'agent':      ['picked_up', 'out_for_delivery', 'delivered'],
    'admin':      list(STATUS_TRANSITIONS.keys()),
    'customer':   ['cancelled'],
}

DISCOUNT_THRESHOLD = 500.00  # Subtotal >= this to get 10% discount
DISCOUNT_RATE = 0.10


def calculate_order_totals(items_with_db_prices, restaurant_delivery_fee):
    """
    Calculate subtotal, discount, delivery fee, and total.
    items_with_db_prices: list of {'food_item_id': x, 'quantity': y, 'price': <from_db>, 'name': ...}
    """
    subtotal = sum(item['price'] * item['quantity'] for item in items_with_db_prices)
    discount = round(subtotal * DISCOUNT_RATE, 2) if subtotal >= DISCOUNT_THRESHOLD else 0.00
    delivery_fee = float(restaurant_delivery_fee)
    total = round(subtotal - discount + delivery_fee, 2)
    return {
        'subtotal': round(subtotal, 2),
        'discount_amount': discount,
        'delivery_fee': delivery_fee,
        'total_amount': total,
        'discount_applied': discount > 0
    }


def validate_and_get_cart_items(cart_items, restaurant_id):
    """
    Validate cart items against DB. Returns validated items or raises ValueError.
    cart_items: [{'food_item_id': int, 'quantity': int}, ...]
    """
    validated = []
    for item in cart_items:
        food_item = execute_query(
            """SELECT id, name, price, is_available, restaurant_id
               FROM food_items
               WHERE id = %s AND restaurant_id = %s""",
            (item['food_item_id'], restaurant_id),
            fetch_one=True
        )
        if not food_item:
            raise ValueError(f"Food item {item['food_item_id']} not found in this restaurant.")
        if not food_item['is_available']:
            raise ValueError(f"'{food_item['name']}' is currently unavailable.")
        if item['quantity'] < 1:
            raise ValueError(f"Invalid quantity for '{food_item['name']}'.")
        validated.append({
            'food_item_id': food_item['id'],
            'name': food_item['name'],
            'price': float(food_item['price']),
            'quantity': item['quantity'],
        })
    return validated


def place_order(customer_id, restaurant_id, cart_items, delivery_address,
                payment_method='cash_on_delivery', special_instructions=''):
    """
    Full order placement with validation and transaction.
    Returns order_id on success.
    """
    # Get restaurant info
    restaurant = execute_query(
        "SELECT id, delivery_fee, is_active FROM restaurants WHERE id = %s",
        (restaurant_id,), fetch_one=True
    )
    if not restaurant or not restaurant['is_active']:
        raise ValueError("Restaurant not found or inactive.")

    # Validate cart items against DB prices
    validated_items = validate_and_get_cart_items(cart_items, restaurant_id)
    if not validated_items:
        raise ValueError("Cart is empty.")

    # Calculate totals
    totals = calculate_order_totals(validated_items, restaurant['delivery_fee'])

    # Build transaction operations
    ops = []

    # 1. Insert order
    ops.append((
        """INSERT INTO orders
           (customer_id, restaurant_id, delivery_address, subtotal,
            discount_amount, delivery_fee, total_amount, status,
            payment_method, special_instructions)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)""",
        (customer_id, restaurant_id, delivery_address,
         totals['subtotal'], totals['discount_amount'],
         totals['delivery_fee'], totals['total_amount'],
         payment_method, special_instructions)
    ))

    # We'll get the order_id after first insert, then add items
    # Use two-step because we need the order_id for items
    from services.database import get_connection
    from mysql.connector import Error as DBError

    conn = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        # Insert order
        cursor.execute(
            """INSERT INTO orders
               (customer_id, restaurant_id, delivery_address, subtotal,
                discount_amount, delivery_fee, total_amount, status,
                payment_method, special_instructions)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)""",
            (customer_id, restaurant_id, delivery_address,
             totals['subtotal'], totals['discount_amount'],
             totals['delivery_fee'], totals['total_amount'],
             payment_method, special_instructions)
        )
        order_id = cursor.lastrowid

        # Insert order items
        for item in validated_items:
            item_total = round(item['price'] * item['quantity'], 2)
            cursor.execute(
                """INSERT INTO order_items
                   (order_id, food_item_id, quantity, unit_price, total_price)
                   VALUES (%s, %s, %s, %s, %s)""",
                (order_id, item['food_item_id'], item['quantity'],
                 item['price'], item_total)
            )

        # Insert initial tracking record
        cursor.execute(
            """INSERT INTO order_tracking (order_id, status, notes, updated_by_role)
               VALUES (%s, 'pending', 'Order placed by customer', 'customer')""",
            (order_id,)
        )

        # Create payment record
        cursor.execute(
            """INSERT INTO payments (order_id, amount, payment_method, payment_status)
               VALUES (%s, %s, %s, 'pending')""",
            (order_id, totals['total_amount'], payment_method)
        )

        # Update customer order count
        cursor.execute(
            "UPDATE customers SET total_orders = total_orders + 1 WHERE id = %s",
            (customer_id,)
        )

        conn.commit()
        return order_id, totals

    except DBError as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.autocommit = True
            conn.close()


def update_order_status(order_id, new_status, updated_by_role, notes='', agent_id=None):
    """Update order status with validation of allowed transitions."""
    order = execute_query(
        "SELECT id, status, delivery_agent_id FROM orders WHERE id = %s",
        (order_id,), fetch_one=True
    )
    if not order:
        raise ValueError("Order not found.")

    current_status = order['status']
    allowed = STATUS_TRANSITIONS.get(current_status, [])
    role_allowed = ROLE_ALLOWED_TRANSITIONS.get(updated_by_role, [])

    if new_status not in allowed:
        raise ValueError(f"Cannot transition from '{current_status}' to '{new_status}'.")
    if new_status not in role_allowed and updated_by_role != 'admin':
        raise ValueError(f"Role '{updated_by_role}' cannot set status '{new_status}'.")

    # Pickup / delivery needs a delivery agent
    if new_status in ('picked_up', 'out_for_delivery', 'delivered') and not (agent_id or order['delivery_agent_id']):
        raise ValueError("Assign a delivery agent to this order first.")

    # Update order
    if agent_id and new_status in ('picked_up', 'out_for_delivery', 'delivered'):
        execute_query(
            "UPDATE orders SET status = %s, delivery_agent_id = %s WHERE id = %s",
            (new_status, agent_id, order_id), commit=True
        )
    else:
        execute_query(
            "UPDATE orders SET status = %s WHERE id = %s",
            (new_status, order_id), commit=True
        )

    # If delivered, update payment and agent stats
    if new_status == 'delivered':
        execute_query(
            "UPDATE payments SET payment_status = 'completed', payment_time = NOW() WHERE order_id = %s",
            (order_id,), commit=True
        )
        if order['delivery_agent_id'] or agent_id:
            aid = agent_id or order['delivery_agent_id']
            execute_query(
                "UPDATE delivery_agents SET total_deliveries = total_deliveries + 1, is_available = 1 WHERE id = %s",
                (aid,), commit=True
            )

    # Cancelled order: release its delivery agent
    if new_status == 'cancelled' and order['delivery_agent_id']:
        execute_query("UPDATE delivery_agents SET is_available = 1 WHERE id = %s",
                      (order['delivery_agent_id'],), commit=True)

    # Record tracking
    execute_query(
        """INSERT INTO order_tracking (order_id, status, notes, updated_by_role)
           VALUES (%s, %s, %s, %s)""",
        (order_id, new_status, notes or f"Status updated to {new_status}", updated_by_role),
        commit=True
    )
    return True


def get_order_details(order_id):
    """Get full order details including items and tracking."""
    order = execute_query(
        """SELECT o.*, c.name as customer_name, c.email as customer_email,
                  r.name as restaurant_name, r.phone as restaurant_phone,
                  da.name as agent_name, da.phone as agent_phone, da.vehicle_number
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN restaurants r ON o.restaurant_id = r.id
           LEFT JOIN delivery_agents da ON o.delivery_agent_id = da.id
           WHERE o.id = %s""",
        (order_id,), fetch_one=True
    )
    if not order:
        return None

    items = execute_query(
        """SELECT oi.*, fi.name as food_name, fi.image_url
           FROM order_items oi
           JOIN food_items fi ON oi.food_item_id = fi.id
           WHERE oi.order_id = %s""",
        (order_id,), fetch=True
    )

    tracking = execute_query(
        """SELECT * FROM order_tracking
           WHERE order_id = %s ORDER BY created_at ASC""",
        (order_id,), fetch=True
    )

    return {'order': order, 'items': items, 'tracking': tracking}
