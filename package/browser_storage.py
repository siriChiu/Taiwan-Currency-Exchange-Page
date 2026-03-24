import json
import uuid

from streamlit_js_eval import streamlit_js_eval

STORAGE_PREFIX = "currency_exchange"


def _storage_key(name: str) -> str:
    return f"{STORAGE_PREFIX}:{name}"


def _js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_text(name: str, default: str | None = None):
    value = streamlit_js_eval(
        js_expressions=f"window.localStorage.getItem({_js_string(_storage_key(name))})",
        want_output=True,
        key=f"local_storage_get_{name}",
    )
    if value in (None, "null", "undefined"):
        return default
    return value


def set_text(name: str, value: str) -> None:
    streamlit_js_eval(
        js_expressions=f"window.localStorage.setItem({_js_string(_storage_key(name))}, {_js_string(value)})",
        want_output=False,
        key=f"local_storage_set_{name}",
    )


def delete_key(name: str) -> None:
    streamlit_js_eval(
        js_expressions=f"window.localStorage.removeItem({_js_string(_storage_key(name))})",
        want_output=False,
        key=f"local_storage_delete_{name}",
    )


def get_json(name: str, default=None):
    raw_value = get_text(name)
    if raw_value in (None, ""):
        return default
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return default


def set_json(name: str, value) -> None:
    set_text(name, json.dumps(value, ensure_ascii=False))


def get_or_create_browser_user_id() -> str:
    existing_id = get_text("browser_user_id")
    if existing_id:
        return existing_id

    generated_id = f"browser_{uuid.uuid4().hex[:24]}"
    set_text("browser_user_id", generated_id)
    return generated_id


def rotate_browser_user_id() -> str:
    generated_id = f"browser_{uuid.uuid4().hex[:24]}"
    set_text("browser_user_id", generated_id)
    return generated_id
