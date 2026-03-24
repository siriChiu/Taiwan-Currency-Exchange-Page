import streamlit as st
import platform
from pathlib import Path
from types import SimpleNamespace
from package import browser_storage
from package import local_storage
from package import validation


def _build_browser_user() -> SimpleNamespace:
    browser_user_id = browser_storage.get_or_create_browser_user_id()
    return SimpleNamespace(id=browser_user_id, email=f"{browser_user_id}@browser.local")


def _sync_subscription_from_google_sheet(user_id: str) -> None:
    try:
        subscription_info = validation.get_subscription_info()
        local_storage.save_subscription(user_id, subscription_info)
        st.session_state['subscription_sync_message'] = None
    except Exception as exc:
        if local_storage.load_subscription(user_id) is None:
            st.error(f"無法從 Google Sheet 驗證訂閱資訊：{exc}")
            st.stop()
        st.session_state['subscription_sync_message'] = (
            f"目前無法連線到 Google Sheet，已改用本機快取的訂閱資料。原因：{exc}"
        )


def _config_exists() -> bool:
    # Check st.secrets first (Streamlit Cloud)
    try:
        _ = st.secrets["operator"]["company"]
        return True
    except (KeyError, Exception):
        pass
    _app_dir = Path.home() / ".currency_app"
    return (_app_dir / "config.ini").exists() or Path("./config.ini").exists()


def _show_registration_form():
    st.title("初次設定")
    st.info("請輸入您的訂閱資訊，需與 Google Sheet 中的記錄相符。")
    with st.form("setup_form"):
        company = st.text_input("公司名稱")
        owner = st.text_input("負責人")
        submitted = st.form_submit_button("確認註冊")
    if submitted:
        if not company or not owner:
            st.error("請填寫所有欄位")
        else:
            ssid = platform.node()
            try:
                validation.write_config(company, owner, ssid)
            except Exception as e:
                st.error(f"無法寫入設定檔：{e}")
                st.stop()
            try:
                validation.update_ssid_in_sheet(company, owner, ssid)
            except Exception as e:
                st.warning(f"設定已儲存，但無法更新 Google Sheet SSID：{e}")
            st.rerun()
    st.stop()


if not _config_exists():
    _show_registration_form()

st.title("Currency Exchange")

default_currency_adjust_config = {
        "USD": 1.3,
        "HKD": 0.15,
        "GBP": 1.5,
        "AUD": 1.2,
        "CAD": 1.2,
        "SGD": 1.2,
        "CHF": 1.3,
        "JPY": 0.012,
        "ZAR": 0.0,
        "SEK": 0.0,
        "NZD": 1.2,
        "THB": 0.05,
        "PHP": 0.05,
        "IDR": 0.0,
        "EUR": 1.5,
        "KRW": 0.0012,
        "VND": 0.0005,
        "MYR": 0.5,
        "CNY": 0.25
    }

if 'currency_adjust_config' not in st.session_state:
    st.session_state.currency_adjust_config = default_currency_adjust_config.copy()

if 'user' not in st.session_state:
    st.session_state['user'] = None
    st.session_state['token'] = None
if 'subscription_sync_message' not in st.session_state:
    st.session_state['subscription_sync_message'] = None

if st.session_state['user'] is None:
    browser_user = _build_browser_user()
    st.session_state['user'] = browser_user
    st.session_state['token'] = "browser-local-token"
    st.session_state['currency_adjust_config'] = browser_storage.get_json(
        "currency_adjust_config",
        default_currency_adjust_config.copy(),
    )
    _sync_subscription_from_google_sheet(browser_user.id)
    st.switch_page("pages/currency_exchange.py")

if st.session_state['user']:
    user_id = st.session_state['user'].id
    st.session_state['currency_adjust_config'] = browser_storage.get_json(
        "currency_adjust_config",
        st.session_state.get('currency_adjust_config', default_currency_adjust_config),
    )
    _sync_subscription_from_google_sheet(user_id)
    st.switch_page("pages/currency_exchange.py")
