import mysql.connector
from mysql.connector import Error, pooling
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection pool
connection_pool = None

def init_pool():
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="food_delivery_pool",
            pool_size=5,
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 3306)),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', 'root'),
            database=os.environ.get('DB_NAME', 'food_delivery'),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False
        )
        print("[DB] Connection pool initialized successfully.")
        return True
    except Error as e:
        print(f"[DB ERROR] Failed to initialize pool: {e}")
        return False

def get_connection():
    """Get a connection from the pool."""
    global connection_pool
    if connection_pool is None:
        init_pool()
    try:
        conn = connection_pool.get_connection()
        return conn
    except Error as e:
        print(f"[DB ERROR] Failed to get connection: {e}")
        raise

def execute_query(query, params=None, fetch=False, fetch_one=False, commit=False):
    """Execute a parameterized SQL query safely."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetch_one:
            return cursor.fetchone()
        if fetch:
            return cursor.fetchall()
        return None
    except Error as e:
        if conn and commit:
            conn.rollback()
        print(f"[DB ERROR] Query failed: {e}\nQuery: {query}\nParams: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_transaction(operations):
    """
    Execute multiple operations in a single transaction.
    operations: list of (query, params) tuples
    Returns: list of lastrowid for each operation
    """
    conn = None
    cursor = None
    results = []
    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)
        for query, params in operations:
            cursor.execute(query, params or ())
            results.append(cursor.lastrowid)
        conn.commit()
        return results
    except Error as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] Transaction failed: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.autocommit = True
            conn.close()

def test_connection():
    """Test database connectivity."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "Connection successful"
    except Error as e:
        return False, str(e)
