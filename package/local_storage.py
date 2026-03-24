import datetime as dt
import json
import sqlite3
from pathlib import Path

ALERT_DAYS_BEFORE_EXPIRY = 7  # 到期前幾天開始顯示警告


def get_user_data_dir(user_id: str) -> Path:
    user_dir = Path.home() / ".currency_app" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_config_path(user_id: str) -> Path:
    return get_user_data_dir(user_id) / "currency_adjust_config.json"


def get_user_db_path(user_id: str) -> Path:
    return get_user_data_dir(user_id) / "currency_history.db"


def init_db(user_id: str) -> None:
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS currency_adjust_current (
                currency TEXT PRIMARY KEY,
                value REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS currency_adjust_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                saved_at TEXT NOT NULL,
                currency TEXT NOT NULL,
                value REAL NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscription (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                registered_date TEXT NOT NULL,
                start_date TEXT NOT NULL,
                alert_date TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                status TEXT NOT NULL,
                service_type TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ── Subscription helpers ──────────────────────────────────────────────────────

def _get_subscription_path(user_id: str) -> Path:
    return get_user_data_dir(user_id) / "subscription.json"


def load_subscription(user_id: str) -> dict | None:
    """Return subscription dict from local JSON, or None if not found."""
    init_db(user_id)
    sub_path = _get_subscription_path(user_id)
    if sub_path.exists():
        try:
            with sub_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _parse_date(date_text: str | None) -> dt.datetime | None:
    if not date_text:
        return None

    cleaned = str(date_text).strip()
    if not cleaned:
        return None

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y.%m.%d",
        "%m-%d-%Y",
        "%m-%d-%y",
    ]
    for date_format in date_formats:
        try:
            return dt.datetime.strptime(cleaned, date_format)
        except ValueError:
            continue
    return None


def save_subscription(user_id: str, subscription_info: dict) -> None:
    """Persist subscription info to JSON and SQLite."""
    init_db(user_id)
    sub_path = _get_subscription_path(user_id)
    with sub_path.open("w", encoding="utf-8") as f:
        json.dump(subscription_info, f, ensure_ascii=False, indent=2)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subscription
                (id, registered_date, start_date, alert_date, expiration_date,
                 status, service_type, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                registered_date  = excluded.registered_date,
                start_date       = excluded.start_date,
                alert_date       = excluded.alert_date,
                expiration_date  = excluded.expiration_date,
                status           = excluded.status,
                service_type     = excluded.service_type,
                updated_at       = excluded.updated_at
            """,
            (
                subscription_info.get("registered_date", ""),
                subscription_info.get("start_date", ""),
                subscription_info.get("alert_date", ""),
                subscription_info.get("expiration_date", ""),
                subscription_info.get("status", "active"),
                subscription_info.get("service_type", "monthly"),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_subscription_status(user_id: str) -> dict:
    """
    Return a dict with:
        sub        – full subscription dict (or None)
        is_expired – bool
        days_left  – int (negative if expired)
        near_expiry – bool (within ALERT_DAYS_BEFORE_EXPIRY days)
    """
    sub = load_subscription(user_id)
    if sub is None:
        return {"sub": None, "is_expired": False, "days_left": None, "near_expiry": False}

    try:
        today = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expiry_text = sub.get("stop_date") or sub.get("expiration_date")
        alert_text = sub.get("alert_date")
        status_text = str(sub.get("status", "active")).strip().lower()

        expiry = _parse_date(expiry_text)
        if expiry is None:
            raise ValueError("Invalid expiration date")
        days_left = (expiry - today).days
        is_expired = days_left < 0 or status_text in {"expired", "inactive", "stopped", "stop"}

        if alert_text:
            alert_date = _parse_date(alert_text)
            if alert_date is None:
                raise ValueError("Invalid alert date")
            near_expiry = alert_date <= today <= expiry and not is_expired
        else:
            near_expiry = 0 <= days_left <= ALERT_DAYS_BEFORE_EXPIRY and not is_expired
    except (KeyError, TypeError, ValueError):
        return {"sub": sub, "is_expired": False, "days_left": None, "near_expiry": False}

    return {
        "sub": sub,
        "is_expired": is_expired,
        "days_left": days_left,
        "near_expiry": near_expiry,
    }


def _normalize_config(config_dict: dict, default_config: dict) -> dict:
    normalized = {}
    for currency, default_value in default_config.items():
        raw_value = config_dict.get(currency, default_value)
        try:
            normalized[currency] = float(raw_value)
        except (TypeError, ValueError):
            normalized[currency] = float(default_value)
    return normalized


def load_config(user_id: str, default_config: dict) -> dict:
    init_db(user_id)
    config_path = get_user_config_path(user_id)

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            return _normalize_config(loaded, default_config)
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    normalized_default = _normalize_config(default_config, default_config)
    save_config(user_id, normalized_default)
    return normalized_default


def save_config(user_id: str, config_dict: dict) -> None:
    init_db(user_id)
    config_path = get_user_config_path(user_id)
    normalized = _normalize_config(config_dict, config_dict)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for currency, value in normalized.items():
            cursor.execute(
                """
                INSERT INTO currency_adjust_current (currency, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(currency)
                DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (currency, float(value), now),
            )
            cursor.execute(
                """
                INSERT INTO currency_adjust_history (saved_at, currency, value)
                VALUES (?, ?, ?)
                """,
                (now, currency, float(value)),
            )
        conn.commit()
    finally:
        conn.close()
