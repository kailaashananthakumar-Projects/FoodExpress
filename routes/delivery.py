"""
Delivery Agent routes: view assigned deliveries, update status.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from routes.auth import login_required
from services.database import execute_query
from services.order_service import update_order_status
from mysql.connector import Error

delivery_bp = Blueprint('delivery', __name__)


@delivery_bp.route('/dashboard')
@login_required(role='agent')
def dashboard():
    agent_id = session['user_id']
    agent = execute_query(
        "SELECT * FROM delivery_agents WHERE id = %s", (agent_id,), fetch_one=True
    )
    
    # Assigned active deliveries
    active_deliveries = execute_query(
        """SELECT o.*, c.name as customer_name, c.phone as customer_phone,
                  r.name as restaurant_name, r.address as restaurant_address,
                  r.phone as restaurant_phone
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN restaurants r ON o.restaurant_id = r.id
           WHERE o.delivery_agent_id = %s
             AND o.status IN ('confirmed','preparing','ready_for_pickup','picked_up','out_for_delivery')
           ORDER BY o.updated_at ASC""",
        (agent_id,), fetch=True
    )
    
    # Completed today
    today_completed = execute_query(
        """SELECT COUNT(*) as cnt FROM orders
           WHERE delivery_agent_id = %s AND status = 'delivered'
             AND DATE(updated_at) = CURDATE()""",
        (agent_id,), fetch_one=True
    )
    
    # Stats
    stats = execute_query(
        """SELECT COUNT(*) as total_delivered,
                  SUM(CASE WHEN DATE(updated_at)=CURDATE() THEN 1 ELSE 0 END) as today_count
           FROM orders WHERE delivery_agent_id = %s AND status = 'delivered'""",
        (agent_id,), fetch_one=True
    )
    
    return render_template('delivery_dashboard.html',
                           agent=agent,
                           active_deliveries=active_deliveries or [],
                           today_completed=today_completed,
                           stats=stats)


@delivery_bp.route('/deliveries')
@login_required(role='agent')
def deliveries():
    agent_id = session['user_id']
    all_deliveries = execute_query(
        """SELECT o.*, c.name as customer_name, c.phone as customer_phone,
                  r.name as restaurant_name, r.address as restaurant_address
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           JOIN restaurants r ON o.restaurant_id = r.id
           WHERE o.delivery_agent_id = %s
           ORDER BY o.created_at DESC""",
        (agent_id,), fetch=True
    )
    return render_template('delivery_history.html', deliveries=all_deliveries or [])


@delivery_bp.route('/orders/<int:order_id>/update', methods=['POST'])
@login_required(role='agent')
def update_delivery_status(order_id):
    agent_id = session['user_id']
    # Security: ensure order is assigned to this agent
    order = execute_query(
        "SELECT id, status FROM orders WHERE id = %s AND delivery_agent_id = %s",
        (order_id, agent_id), fetch_one=True
    )
    if not order:
        flash('Order not assigned to you.', 'danger')
        return redirect(url_for('delivery.dashboard'))
    
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    try:
        update_order_status(order_id, new_status, 'agent', notes, agent_id=agent_id)
        # Mark agent as available if delivery complete
        if new_status == 'delivered':
            execute_query(
                "UPDATE delivery_agents SET is_available = 1 WHERE id = %s",
                (agent_id,), commit=True
            )
        flash(f'Delivery status updated to "{new_status}".', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('delivery.dashboard'))
