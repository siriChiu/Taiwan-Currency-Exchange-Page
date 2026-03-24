import streamlit as st
from types import SimpleNamespace
from package import browser_storage
from package import local_storage
from package import validation


st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _build_browser_user() -> SimpleNamespace:
    browser_user_id = browser_storage.get_or_create_browser_user_id()
    return SimpleNamespace(id=browser_user_id, email=f"{browser_user_id}@browser.local")


def _sync_subscription_from_google_sheet(user_id: str, identity: dict) -> None:
    try:
        subscription_info = validation.get_subscription_info_for_user(
            company=identity["company"],
            owner=identity["owner"],
            ssid=identity.get("ssid", ""),
        )
        local_storage.save_subscription(user_id, subscription_info)
        st.session_state['subscription_sync_message'] = None
    except Exception as exc:
        if local_storage.load_subscription(user_id) is None:
            st.error(f"無法從 Google Sheet 驗證訂閱資訊：{exc}")
            st.stop()
        st.session_state['subscription_sync_message'] = (
            f"目前無法連線到 Google Sheet，已改用本機快取的訂閱資料。原因：{exc}"
        )


def _get_or_prompt_user_identity() -> dict:
    force_prompt = bool(st.session_state.get('force_identity_prompt'))

    session_identity = st.session_state.get('user_identity')
    if (not force_prompt) and isinstance(session_identity, dict) and session_identity.get("company") and session_identity.get("owner"):
        return session_identity

    identity = None if force_prompt else browser_storage.get_json("user_identity")
    if isinstance(identity, dict) and identity.get("company") and identity.get("owner"):
        return identity

    st.info("請先輸入您的公司與負責人，我們會對照 Google Sheet 驗證您的身分。")

    with st.form("identity_form"):
        company = st.text_input("公司名稱")
        owner = st.text_input("負責人")
        submit = st.form_submit_button("驗證並繼續")

    if submit:
        company = company.strip()
        owner = owner.strip()
        if not company or not owner:
            st.error("請填寫公司名稱與負責人。")
            st.stop()
        try:
            validation.get_subscription_info_for_user(company=company, owner=owner, ssid="")
            identity = {"company": company, "owner": owner, "ssid": ""}
            st.session_state['user_identity'] = identity
            st.session_state['force_identity_prompt'] = False
            browser_storage.set_json("user_identity", identity)
            return identity
        except Exception as exc:
            st.error(f"驗證失敗：{exc}")

    st.stop()

st.title("Currency Exchange")

default_currency_adjust_config = {
        "USD": 1.20,
        "HKD": 0.13,
        "GBP": 1.4,
        "AUD": 1.2,
        "CAD": 1.21,
        "SGD": 1.22,
        "CHF": 1.45,
        "JPY": 0.012,
        "ZAR": 0.0,
        "SEK": 0.0,
        "NZD": 1.22,
        "THB": 0.05,
        "PHP": 0.05,
        "IDR": 0.000095,
        "EUR": 1.3,
        "KRW": 0.00105,
        "VND": 0.0000884,
        "MYR": 0.5,
        "CNY": 0.3
    }

if 'currency_adjust_config' not in st.session_state:
    st.session_state.currency_adjust_config = default_currency_adjust_config.copy()

if 'user' not in st.session_state:
    st.session_state['user'] = None
    st.session_state['token'] = None
if 'subscription_sync_message' not in st.session_state:
    st.session_state['subscription_sync_message'] = None
if 'user_identity' not in st.session_state:
    st.session_state['user_identity'] = None
if 'force_identity_prompt' not in st.session_state:
    st.session_state['force_identity_prompt'] = False

if st.session_state['user'] is None:
    browser_user = _build_browser_user()
    identity = _get_or_prompt_user_identity()
    st.session_state['user'] = browser_user
    st.session_state['user_identity'] = identity
    st.session_state['token'] = "browser-local-token"
    st.session_state['currency_adjust_config'] = browser_storage.get_json(
        "currency_adjust_config",
        default_currency_adjust_config.copy(),
    )
    _sync_subscription_from_google_sheet(browser_user.id, identity)
    st.switch_page("pages/currency_exchange.py")

if st.session_state['user']:
    user_id = st.session_state['user'].id
    identity = st.session_state.get('user_identity') or _get_or_prompt_user_identity()
    st.session_state['user_identity'] = identity
    st.session_state['currency_adjust_config'] = browser_storage.get_json(
        "currency_adjust_config",
        st.session_state.get('currency_adjust_config', default_currency_adjust_config),
    )
    _sync_subscription_from_google_sheet(user_id, identity)
    st.switch_page("pages/currency_exchange.py")
