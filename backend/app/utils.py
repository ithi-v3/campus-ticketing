from flask import request

from .errors import ApiError


def get_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Send a JSON body.")
    return data


def get_str(data, field, max_len, required=True):
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ApiError(f"{field.replace('_', ' ').capitalize()} is required.")
        return None
    if not isinstance(value, str):
        raise ApiError(f"{field.replace('_', ' ').capitalize()} must be text.")
    value = value.strip()
    if len(value) > max_len:
        raise ApiError(f"{field.replace('_', ' ').capitalize()} must be at most {max_len} characters.")
    return value


def get_int(data, field, required=True):
    value = data.get(field)
    if value is None or value == "":
        if required:
            raise ApiError(f"{field.replace('_', ' ').capitalize()} is required.")
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field.replace('_', ' ').capitalize()} must be a number.")


def page_args(default_per_page=10, max_per_page=50):
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", default_per_page))
    except ValueError:
        raise ApiError("page and per_page must be numbers.")
    return page, min(max(per_page, 1), max_per_page)
