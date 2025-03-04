global cnx
import os
import mysql.connector
from urllib.parse import urlparse

# Get Database URL from Environment Variables
'''
DATABASE_URL = os.getenv("DATABASE_URL")

# Parse the MySQL connection string
if DATABASE_URL:
    db_config = DATABASE_URL.replace("mysql://", "").split("@")
    user_pass, host_db = db_config[0].split(":"), db_config[1].split("/")
    username, password = user_pass[0], user_pass[1]
    host_port, database = host_db[0].split(":"), host_db[1]

    host, port = host_port[0], int(host_port[1])

    # Establish Connection
    cnx = mysql.connector.connect(
        user=username,
        password=password,
        host=host,
        port=port,
        database=database
    )
else:
    raise ValueError("DATABASE_URL environment variable is not set!")

'''
import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    db_config = DATABASE_URL.replace("mysql://", "").split("@")
    user_pass, host_db = db_config[0].split(":"), db_config[1].split("/")
    username, password = user_pass[0], user_pass[1]
    host_port, database = host_db[0].split(":"), host_db[1]

    host, port = host_port[0], int(host_port[1])

    # Establish Connection
    cnx = mysql.connector.connect(
        user=username,
        password=password,
        host=host,
        port=port,
        database=database
    )
    print("✅ Connected to MySQL successfully!")
else:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Function to get database connection
def get_db_connection():
    if not cnx.is_connected():
        cnx.reconnect()
    return cnx


def insert_order_item(food_name, quantity, order_id):
    """Inserts an item into the orders table by looking up item_id and price from the food_items table."""
    cursor = cnx.cursor()

    try:
        # ✅ Fetch item_id and price from food_items table
        query = "SELECT item_id, price FROM food_items WHERE name = %s"
        cursor.execute(query, (food_name,))
        result = cursor.fetchone()

        if not result:
            return -1  # Return error if food item does not exist

        item_id, price = result
        total_price = price * quantity  # ✅ Calculate total price

        # ✅ Insert into orders table
        insert_query = "INSERT INTO orders (order_id, item_id, quantity, total_price) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (order_id, item_id, quantity, total_price))

        cnx.commit()  # ✅ Commit transaction

        print(f"✅ Order inserted: {quantity}x {food_name} (Order ID: {order_id}, Total: {total_price})")
        return 1  # ✅ Success

    except mysql.connector.Error as e:
        print(f"🚨 Database Error: {e}")
        cnx.rollback()  # ✅ Rollback in case of error
        return -1  # ✅ Return failure

    finally:
        cursor.close()  # ✅ Always close the cursor




def insert_order_tracking(order_id, status):
    """Inserts order tracking status into the database."""
    cursor = cnx.cursor()
    try:
        query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
        cursor.execute(query, (order_id, status))
        cnx.commit()  # Commit changes
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        cnx.rollback()  # Rollback on error
    finally:
        cursor.close()  # Ensure cursor closes


def get_total_order_price(order_id):
    """Retrieves the total price of an order safely."""
    cursor = cnx.cursor()
    try:
        query = "SELECT get_total_order_price(%s)"  # ✅ Fix: Parameterized Query
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        if result is None:
            return 0  # Default to 0 if no result
        return result[0]
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return -1  # Return -1 on failure
    finally:
        cursor.close()  # Ensure cursor closes


def get_next_order_id():
    """Fetches the next available order_id."""
    cursor = cnx.cursor()
    try:
        query = "SELECT MAX(order_id) FROM orders"
        cursor.execute(query)
        result = cursor.fetchone()[0]

        return 1 if result is None else result + 1  # ✅ Fix: Safe Handling of `None`
    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
        return -1  # Return -1 if database error occurs
    finally:
        cursor.close()  # Ensure cursor closes


def get_order_status(order_id):
    cursor = cnx.cursor()

    # Executing the SQL query to fetch the order status
    query = f"SELECT status FROM order_tracking WHERE order_id = {order_id}"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()

    # Closing the cursor
    cursor.close()

    # Returning the order status
    if result:
        return result[0]
    else:
        return None

