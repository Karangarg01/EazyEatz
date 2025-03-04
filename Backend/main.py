import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import spacy

from spacy.pipeline.span_ruler import prioritize_new_ents_filter

import db_helper
import generic_helper
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

app = FastAPI()
inprogress_orders= {}

# Enable logging
logging.basicConfig(level=logging.DEBUG)
''''
@app.get("/")

async def root():
    return {"HelloS"}

'''
@app.post("/")

async def dialogflow_webhook(request: Request):
    """Handles Dialogflow webhook requests."""

    payload = await request.json()
    # logging.debug(f"Received Payload: {payload}")

    query_result = payload.get("queryResult", {})
    intent = query_result.get("intent", {}).get("displayName", "")
    parameters = query_result.get("parameters", {})

    output_contexts = query_result.get("outputContexts", [])

    # Extract session ID
    session_id = generic_helper.extract_session_id(output_contexts[0]["name"]) if output_contexts else ""

    # logging.debug(f"Intent: {intent}, Parameters: {parameters}, Session: {session_id}")

    # Intent mapping for better structure
    intent_handlers= {
        'order.add-context: ongoing-order': add_to_order,
        'order.remove-context: ongoing-order': remove_from_order,
        'complete.order-context: ongoing-order': complete_order,
        'track.order-context: ongoing-tracking': track_order
    }

    # Call the respective function or return default response
    if intent in intent_handlers:
        return await intent_handlers[intent](parameters, session_id)

    # logging.warning(f"Unrecognized intent: {intent}")
    return JSONResponse(content={"fulfillmentText": "Intent not recognized."})


async def track_order(parameters: dict, session_id: str):
    """Handles 'track order' intent."""
    order_id = int(parameters.get("order_id"))

    if not order_id or not str(order_id).isdigit():
        return JSONResponse(content={"fulfillmentText": "Invalid order ID. Please provide a numeric order ID."})

    order_id = int(order_id)
    # logging.debug(f"Extracted Order ID: {order_id}")

    try:
        order_status = await asyncio.to_thread(db_helper.get_order_status, order_id)
    except Exception as e:
        logging.error(f"Database query failed: {e}")
        return JSONResponse(content={"fulfillmentText": "Sorry, an error occurred while fetching the order status."})

    if order_status:
        fulfillment_text = f"The current status of order {order_id} is: {order_status}."
    else:
        fulfillment_text = f"Sorry, I couldn't find an order with ID {order_id}."

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


async def add_to_order(parameters: dict, session_id: str):
    """
    Adds items to the temporary order buffer from Dialogflow parameters.
    Stores data in the format: {quantity: food_item}.
    """
    quantities = parameters.get("number", [])
    food_items = parameters.get("food_item", [])

    if not food_items:
        return JSONResponse(content={"fulfillmentText": "I didn't catch the food items. Could you repeat that?"})

    if len(food_items) != len(quantities):
        return JSONResponse(content={"fulfillmentText": "Please provide a quantity for each food item."})

    # Ensure quantities are integers and store each item separately
    new_food_dict = {}
    for qty, item in zip(quantities, food_items):
        qty = int(qty)  # Convert float to int
        if qty in new_food_dict:
            new_food_dict[qty].append(item)  # Store multiple items separately
        else:
            new_food_dict[qty] = [item]

    # Check if session exists and update instead of replacing
    if session_id in inprogress_orders:
        current_food_dict = inprogress_orders[session_id]

        for qty, items in new_food_dict.items():
            if qty in current_food_dict:
                current_food_dict[qty].extend(items)  # Append items separately
            else:
                current_food_dict[qty] = items  # Add new quantity entry

    else:
        inprogress_orders[session_id] = new_food_dict  # Create new order entry

    print("Updated order dictionary:", inprogress_orders)

    order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
    fulfillment_text = f"So far, you have ordered: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})



async def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having trouble finding your order. Can you place a new one?"
        })

    food_items = parameters.get("food_item", [])
    if not food_items:
        return JSONResponse(content={
            "fulfillmentText": "Please specify which items you want to remove."
        })

    current_order = inprogress_orders[session_id]
    removed_items = []
    no_such_items = []
    keys_to_remove = []

    for item in food_items:
        found_key = None
        for quantity, food_list in list(current_order.items()):
            if isinstance(food_list, list) and food_list[0].lower() == item.lower():
                found_key = quantity
                break  # Stop searching once found

        if found_key is not None:
            removed_items.append(f"{current_order[found_key][0]} {found_key} ")
            keys_to_remove.append(found_key)
        else:
            no_such_items.append(item)

    # Remove items after loop to avoid modifying dictionary mid-iteration
    for key in keys_to_remove:
        del current_order[key]

    fulfillment_text = ""

    if removed_items:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order! "

    if no_such_items:
        fulfillment_text += f"Your current order does not have {', '.join(no_such_items)}. "

    if not current_order:
        fulfillment_text += "Your order is now empty!"
        del inprogress_orders[session_id]
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f"Here is what remains in your order: {order_str}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})





async def save_to_db(order: dict):
    """Saves the order to the database and returns the order ID."""
    next_order_id = db_helper.get_next_order_id()

    # Insert each food item with its quantity into the database
    for quantity, food_items in order.items():
        for food_item in food_items:  # Handle multiple items per quantity
            rcode = db_helper.insert_order_item(
                food_item,
                quantity,
                next_order_id
            )
            if rcode == -1:
                return -1  # Return error if DB insertion fails

    # Insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id # Return the new order ID


async def complete_order(parameters: dict, session_id: str):
    """Finalizes an order, saves it to the database, and returns a confirmation message."""
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order, please?"
        })

    # Retrieve order details and save to DB
    order = inprogress_orders[session_id]
    order_id = await save_to_db(order)  # 🔹 FIX: Added `await`

    if order_id == -1:
        fulfillment_text = (
            f"Food item is not available in the Menu. Please order from the menu only!"

        )
    else:
        order_total = db_helper.get_total_order_price(order_id)
        fulfillment_text = (
            f"Awesome! Your order has been placed successfully. "
            f"Here is your order ID: #{order_id}. "
            f"Your total is {order_total}, payable upon delivery!"
        )

    # Remove session data after order completion
    del inprogress_orders[session_id]

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

