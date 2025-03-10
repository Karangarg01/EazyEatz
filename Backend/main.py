import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import spacy
import db_helper
import generic_helper

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

app = FastAPI()
inprogress_orders = {}

# Enable logging
logging.basicConfig(level=logging.DEBUG)


@app.post("/")
async def dialogflow_webhook(request: Request):
    """Handles Dialogflow webhook requests."""
    payload = await request.json()
    query_result = payload.get("queryResult", {})
    intent = query_result.get("intent", {}).get("displayName", "")
    parameters = query_result.get("parameters", {})
    output_contexts = query_result.get("outputContexts", [])

    session_id = generic_helper.extract_session_id(output_contexts[0]["name"]) if output_contexts else ""

    intent_handlers = {
        'order.add-context: ongoing-order': add_to_order,
        'order.remove-context: ongoing-order': remove_from_order,
        'complete.order-context: ongoing-order': complete_order,
        'track.order-context: ongoing-tracking': track_order
    }

    if intent in intent_handlers:
        return await intent_handlers[intent](parameters, session_id)

    return JSONResponse(content={"fulfillmentText": "Intent not recognized."})


async def track_order(parameters: dict, session_id: str):
    """Handles 'track order' intent."""
    order_id = parameters.get("order_id")

    if not order_id or not str(order_id).isdigit():
        return JSONResponse(content={"fulfillmentText": "Invalid order ID. Please provide a numeric order ID."})

    order_id = int(order_id)

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


def add_to_order(parameters: dict, session_id: str):
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.debug(f"Received parameters: {parameters}")

    # Extract food items and quantities safely
    food_items = parameters.get("food_item", [])
    quantities = parameters.get("number", [])

    # Ensure we get single values instead of lists if needed
    if isinstance(food_items, list) and len(food_items) == 1:
        food_items = food_items  # Already a list with 1 element
    if isinstance(quantities, list) and len(quantities) == 1:
        quantities = [int(quantities[0])]  # Convert to int

    # Validate that we have equal numbers of items and quantities
    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry, I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        # Create an order dictionary
        new_food_dict = dict(zip(food_items, quantities))

        # Merge with an existing order if present
        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            for item, qty in new_food_dict.items():
                current_food_dict[item] = current_food_dict.get(item, 0) + qty
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict

        # Generate a readable order string
        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    logging.debug(f"Final Order: {inprogress_orders[session_id]}")
    return JSONResponse(content={"fulfillmentText": fulfillment_text})



async def remove_from_order(parameters: dict, session_id: str):
    """Removes items from the ongoing order."""
    if session_id not in inprogress_orders:
        return JSONResponse(content={"fulfillmentText": "I'm having trouble finding your order. Can you place a new one?"})

    food_items = parameters.get("food_item", [])
    if not food_items:
        return JSONResponse(content={"fulfillmentText": "Please specify which items you want to remove."})

    current_order = inprogress_orders[session_id]
    updated_order = [order for order in current_order if order[1] not in food_items]

    removed_items = [order[1] for order in current_order if order[1] in food_items]
    fulfillment_text = ""

    if removed_items:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order! "

    if not updated_order:
        fulfillment_text += "Your order is now empty!"
        del inprogress_orders[session_id]
    else:
        inprogress_orders[session_id] = updated_order
        order_str = generic_helper.get_str_from_food_dict(updated_order)
        fulfillment_text += f"Here is what remains in your order: {order_str}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


async def save_to_db(order: list):
    """Saves the order to the database."""
    next_order_id = db_helper.get_next_order_id()

    for quantity, food_item in order:
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if rcode == -1:
            return -1

    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id


async def complete_order(parameters: dict, session_id: str):
    """Finalizes an order and saves it to the database."""
    if session_id not in inprogress_orders:
        return JSONResponse(content={"fulfillmentText": "I'm having trouble finding your order. Can you place a new order?"})

    order = inprogress_orders[session_id]
    order_id = await save_to_db(order)

    if order_id == -1:
        fulfillment_text = "Food item is not available in the menu. Please order from the menu only!"
    else:
        order_total = db_helper.get_total_order_price(order_id)
        fulfillment_text = f"Awesome! Your order has been placed successfully. Your order ID is #{order_id}. Your total is {order_total}, payable upon delivery!"

    del inprogress_orders[session_id]

    return JSONResponse(content={"fulfillmentText": fulfillment_text})
