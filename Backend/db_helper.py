import os
import mysql.connector
from sqlalchemy import create_engine

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.getenv(r"mysql://root:czQQnVPjEscYzwtXJcUHoGmcOInfPDfy@shortline.proxy.rlwy.net:34427/railway")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Create database connection details manually (since `pymysql` is removed)
DB_HOST = os.getenv("DB_HOST", "shortline.proxy.rlwy.net")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "czQQnVPjEscYzwtXJcUHoGmcOInfPDfy")
DB_NAME = os.getenv("DB_NAME", "railway")
DB_PORT = int(os.getenv("DB_PORT", 34427))

# Create MySQL connection
def get_db_connection():
    """Creates and returns a new MySQL connection using mysql-connector-python."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

# Establish a global connection
cnx = get_db_connection()

# Function to check if connection works
def test_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"✅ Connected to Database: {result[0]}"
    except mysql.connector.Error as e:
        return f"🚨 Database Error: {e}"

# Example usage:
print(test_connection())


# Global connection object
cnx = get_db_connection()

def insert_order_item(food_name, quantity, order_id):
    """Inserts an item into the orders table by looking up item_id and price from the food_items table."""
    cursor = cnx.cursor()
    try:
        query = "SELECT item_id, price FROM food_items WHERE name = %s"
        cursor.execute(query, (food_name,))
        result = cursor.fetchone()

        if not result:
            return -1

        item_id, price = result
        total_price = price * quantity

        insert_query = "INSERT INTO orders (order_id, item_id, quantity, total_price) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (order_id, item_id, quantity, total_price))

        cnx.commit()
        return 1

    except mysql.connector.Error as e:
        print(f"🚨 Database Error: {e}")
        cnx.rollback()
        return -1

    finally:
        cursor.close()

def insert_order_tracking(order_id, status):
    """Inserts order tracking status into the database."""
    cursor = cnx.cursor()
    try:
        query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
        cursor.execute(query, (order_id, status))
        cnx.commit()
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        cnx.rollback()
    finally:
        cursor.close()

def get_total_order_price(order_id):
    """Retrieves the total price of an order safely."""
    cursor = cnx.cursor()
    try:
        query = "SELECT get_total_order_price(%s)"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        return result[0] if result else 0
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return -1
    finally:
        cursor.close()

def get_next_order_id():
    """Fetches the next available order_id."""
    cursor = cnx.cursor()
    try:
        query = "SELECT MAX(order_id) FROM orders"
        cursor.execute(query)
        result = cursor.fetchone()[0]

        return 1 if result is None else result + 1
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return -1
    finally:
        cursor.close()

def get_order_status(order_id):
    """Fetches order status."""
    cursor = cnx.cursor()
    try:
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()

if __name__ == '__main__':
    test_connection()