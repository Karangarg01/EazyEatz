import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import db_helper
import generic_helper

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
    intent_handlers = {
        "track.order-context: ongoing-tracking": track_order,
        "order.add-context: ongoing-order": add_to_order,
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
    """
    quantities = parameters.get("number")
    food_items = parameters.get("food_item")

    if not food_items:
        return JSONResponse(content={"fulfillmentText": "I didn't catch the food items. Could you repeat that?"})

    # Ensure lists are the same length
    if len(food_items) != len(quantities):
        return JSONResponse(content={"fulfillmentText": "Please provide a quantity for each food item."})

    new_food_dict = dict(zip(quantities, food_items))

    if session_id in inprogress_orders:
        current_food_dict = inprogress_orders[session_id]
        current_food_dict.update(new_food_dict)
        inprogress_orders[session_id] = current_food_dict

    else:
        inprogress_orders[session_id] = new_food_dict

        # session_id ---> dict
        # 456 --> {2:'Pizza'}

    print(inprogress_orders)
    order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
    print(order_str)
    fulfillment_text = f"So far, you have ordered: {order_str}. Do you need anything else?, {inprogress_orders[session_id]}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})
