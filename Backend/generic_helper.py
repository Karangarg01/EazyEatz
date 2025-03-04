import re

def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{qty} {item}" for qty, items in food_dict.items() for item in items])
    return result


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string

    return ""

# if __name__ == "__main__":
#     q = [2,4]
#     f = ['P', 'B']
#
#     new = dict(zip(q,f))
#     print(get_str_from_food_dict(new))
    # print(extract_session_id("projects/alice-xmuu/agent/sessions/64/contexts/ongoing-order"))