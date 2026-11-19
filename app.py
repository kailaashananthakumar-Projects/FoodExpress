"""
Food Delivery Management System - Main Application Entry Point
"""
import os
import sys

# Ensure the project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, redirect, url_for, session
from config import Config
from services.database import init_pool, test_connection

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database connection pool
with app.app_context():
    init_pool()

# Register blueprints
from routes.auth import auth_bp
from routes.customer import customer_bp
from routes.restaurant import restaurant_bp
from routes.delivery import delivery_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp, url_prefix='/customer')
app.register_blueprint(restaurant_bp, url_prefix='/restaurant')
app.register_blueprint(delivery_bp, url_prefix='/delivery')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Main routes
@app.route('/')
def index():
    from services.database import execute_query
    featured_restaurants = execute_query(
        "SELECT * FROM restaurants WHERE is_active=1 ORDER BY rating DESC LIMIT 6",
        fetch=True
    )
    categories = execute_query(
        "SELECT * FROM categories WHERE is_active=1 ORDER BY name LIMIT 8",
        fetch=True
    )
    stats = execute_query(
        """SELECT
             (SELECT COUNT(*) FROM customers) as customers,
             (SELECT COUNT(*) FROM restaurants WHERE is_active=1) as restaurants,
             (SELECT COUNT(*) FROM orders WHERE status='delivered') as deliveries""",
        fetch_one=True
    )
    return render_template('index.html',
                           featured_restaurants=featured_restaurants or [],
                           categories=categories or [],
                           stats=stats)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/health')
def health():
    ok, msg = test_connection()
    return {'status': 'ok' if ok else 'error', 'db': msg}, 200 if ok else 500


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Internal Server Error'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Forbidden'), 403


if __name__ == '__main__':
    print("=" * 60)
    print("  Food Delivery Management System")
    print("  Starting on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=app.config.get('DEBUG', True)
    )
