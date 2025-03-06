import re

def get_str_from_food_dict(order_dict: dict):
    """Converts a dictionary of {item: quantity} into a readable string."""
    return ", ".join([f"{qty} {item}" for item, qty in order_dict.items()])


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        return match.group(1)

    return ""
