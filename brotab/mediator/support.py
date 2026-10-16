def is_valid_integer(str_value):
    try:
        return int(str_value) >= 0
    except (ValueError, TypeError):
        return False