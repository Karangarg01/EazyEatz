import re

def get_str_from_food_dict(order_list: list):
    """
    Converts a list of (quantity, food_item) tuples into a readable string.
    """
    return ", ".join(f"{qty} {item}" for qty, item in order_list)


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        return match.group(1)

    return ""
