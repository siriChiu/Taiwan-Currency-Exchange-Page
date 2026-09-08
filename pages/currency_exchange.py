import streamlit as st
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
from package import browser_storage
from package import local_storage
from package import ui_style
from package import validation
st.set_page_config(
    page_title="currency exchange",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui_style.hide_streamlit_cloud_badge()

DEFAULT_CURRENCY_ADJUST_CONFIG = {
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
    "KRW": 0.00123,
    "VND": 0.000064,
    "MYR": 0.5,
    "CNY": 0.25
}

if (
    'user' not in st.session_state
    or 'token' not in st.session_state
    or st.session_state.get('user') is None
    or st.session_state.get('token') is None
):
    st.switch_page("main.py")
    st.stop()


def _switch_user_and_reverify() -> None:
    browser_storage.delete_key("user_identity")
    browser_storage.delete_key("currency_adjust_config")
    browser_storage.rotate_browser_user_id()
    st.session_state['force_identity_prompt'] = True
    st.session_state['user_identity'] = None
    st.session_state['currency_adjust_config'] = {
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

    st.session_state['user'] = None
    st.session_state['token'] = None
    st.session_state['subscription_sync_message'] = None
    st.switch_page("main.py")
    st.stop()

user_id = st.session_state['user'].id
identity = st.session_state.get('user_identity') or browser_storage.get_json("user_identity")

if not identity or not identity.get("company") or not identity.get("owner"):
    st.warning("找不到使用者識別資料，請重新驗證。")
    _switch_user_and_reverify()

try:
    latest_subscription = validation.get_subscription_info_for_user(
        company=identity["company"],
        owner=identity["owner"],
        ssid=identity.get("ssid", ""),
    )
    local_storage.save_subscription(user_id, latest_subscription)
    st.session_state['subscription_sync_message'] = None
except Exception as exc:
    if local_storage.load_subscription(user_id) is None:
        st.error(f"無法從 Google Sheet 驗證訂閱資訊：{exc}")
        st.stop()
    st.session_state['subscription_sync_message'] = (
        f"目前無法連線到 Google Sheet，已改用本機快取的訂閱資料。原因：{exc}"
    )

if st.session_state.get('subscription_sync_message'):
    st.info(st.session_state['subscription_sync_message'], icon="ℹ️")

# st.caption("匯率設定會儲存在此瀏覽器的 localStorage 中。更換瀏覽器、清除網站資料或使用無痕模式時，設定可能不會保留。")

# ── Subscription check ────────────────────────────────────────────────────────
_sub_status = local_storage.get_subscription_status(user_id)
if _sub_status["is_expired"]:
    st.error(
        "您的訂閱已到期，無法繼續使用。\n\n"
        f"到期日：{_sub_status['sub']['expiration_date']}\n\n"
        "請聯絡管理員續訂。",
        icon="⛔",
    )
    if st.button("切換使用者重新驗證", use_container_width=True):
        _switch_user_and_reverify()
    st.stop()
elif _sub_status["near_expiry"]:
    days = _sub_status["days_left"]
    expiry_date = _sub_status["sub"]["expiration_date"]
    st.warning(
        f"您的訂閱將在 **{days} 天後**（{expiry_date}）到期，請儘早聯絡管理員續訂。",
        icon="⚠️",
    )
# ─────────────────────────────────────────────────────────────────────────────

if 'currency_adjust_config' not in st.session_state:
    st.session_state['currency_adjust_config'] = dict(DEFAULT_CURRENCY_ADJUST_CONFIG)

if 'currency_adjust_config_loaded' not in st.session_state:
    stored_currency_adjust_config = browser_storage.get_json("currency_adjust_config")
    if stored_currency_adjust_config:
        st.session_state['currency_adjust_config'] = stored_currency_adjust_config
    st.session_state['currency_adjust_config_loaded'] = True

user_currency_adjust_dict = dict(st.session_state['currency_adjust_config'])


def render_settings_sidebar(saved_currency_adjust_dict):
    active_currency_adjust_dict = dict(saved_currency_adjust_dict)

    with st.sidebar:
        with st.expander("設定",icon="⚙️", expanded=True):
            # st.write("螢幕方向")
            # st.radio("螢幕方向", ["橫向", "直向"], index=0, key="screen_side", label_visibility="collapsed")

            st.caption("每位使用者的匯率設定會儲存在此瀏覽器（localStorage）。")

            st.write("校正匯率")
            with st.form(key="currency_adjust_form", enter_to_submit=False):
                draft_currency_adjust_dict = {}
                for key, value in saved_currency_adjust_dict.items():
                    column1, column2 = st.columns([1, 3])
                    with column1:
                        st.write(key)
                    with column2:
                        draft_currency_adjust_dict[key] = st.number_input(
                            key,
                            value=float(value),
                            step=0.0000001,
                            format="%.7f",
                            key=f"currency_adjust_{key}",
                            label_visibility="collapsed",
                        )

                submit_button = st.form_submit_button(label="確定", type="primary")
                if submit_button:
                    browser_storage.set_json("currency_adjust_config", draft_currency_adjust_dict)
                    st.session_state['currency_adjust_config'] = dict(draft_currency_adjust_dict)
                    st.session_state['currency_adjust_config_loaded'] = True
                    active_currency_adjust_dict = dict(draft_currency_adjust_dict)
                    st.success("已儲存到此瀏覽器的個人匯率設定")
            

            # if st.button("Logout"):
            #     st.session_state['user'] = None
            #     st.session_state['token'] = None
            #     st.switch_page("main.py")
            if st.button("切換使用者", use_container_width=True):
                _switch_user_and_reverify()

    return active_currency_adjust_dict


user_currency_adjust_dict = render_settings_sidebar(user_currency_adjust_dict)


count = st_autorefresh(interval=14400000, key="parseCurrencyRate") # refresh every 4 hours

st.html("""
    <style>
        .stMainBlockContainer {
            padding: 6rem 0rem 10rem 1rem ;
        }
    </style>
    """
)

st.html(
    """<style>
    /* Style columns */
    [data-testid="stHeader"]  {
        height: 10px;
    } 
    </style>""",
)

# hide header link
st.html(
    body="""
        <style>
            [data-testid="stHeaderActionElements"]  {
                display: none !important;
            }
            [data-testid="stTooltipHoverTarget"]  {
                display: none !important;
            }
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
        </style>
    """,
)

st.html("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@100&display=swap'); 
            body * {
                font-size: 30px;
                font-weight: 500;
                color: #091747;
            }
            </style>
            """)

st.markdown(
    """
        <a href='https://rate.bot.com.tw/xrt?Lang=zh-TW' style='
        text-align: center; display: block; text-decoration:none; color: #232323; padding: 1rem; font-weight: bold; font-size: xxx-large;
        '>台灣銀行牌告匯率 (Bank of Taiwan Exchange Rates)</a>
    """, unsafe_allow_html=True)

st.markdown(
    """
    <a href='https://rate.bot.com.tw/xrt?Lang=zh-TW'  style="background-color: #b91a46; width: 100%;  display: flex; 
                justify-content: center; align-items: center;">
        <img src="https://rate.bot.com.tw/Content/images/logo.png" style="max-width: 100%; max-height: 90%; height: 5rem;">
    </a>
    """,
    unsafe_allow_html=True
)
contry_image_dict = {
    "USD": "https://flagicons.lipis.dev/flags/4x3/us.svg",
    "HKD": "https://flagicons.lipis.dev/flags/4x3/hk.svg",
    "GBP": "https://flagicons.lipis.dev/flags/4x3/gb.svg",
    "AUD": "https://flagicons.lipis.dev/flags/4x3/au.svg",
    "CAD": "https://flagicons.lipis.dev/flags/4x3/ca.svg",
    "SGD": "https://flagicons.lipis.dev/flags/4x3/sg.svg",
    "CHF": "https://flagicons.lipis.dev/flags/4x3/ch.svg",
    "JPY": "https://flagicons.lipis.dev/flags/4x3/jp.svg",
    "ZAR": "https://flagicons.lipis.dev/flags/4x3/za.svg",
    "SEK": "https://flagicons.lipis.dev/flags/4x3/se.svg",
    "NZD": "https://flagicons.lipis.dev/flags/4x3/nz.svg",
    "THB": "https://flagicons.lipis.dev/flags/4x3/th.svg",
    "PHP": "https://flagicons.lipis.dev/flags/4x3/ph.svg",
    "IDR": "https://flagicons.lipis.dev/flags/4x3/id.svg",
    "EUR": "https://flagicons.lipis.dev/flags/4x3/eu.svg",
    "KRW": "https://flagicons.lipis.dev/flags/4x3/kr.svg",
    "VND": "https://flagicons.lipis.dev/flags/4x3/vn.svg",
    "MYR": "https://flagicons.lipis.dev/flags/4x3/my.svg",
    "CNY": "https://flagicons.lipis.dev/flags/4x3/cn.svg",
}

CURRENCY_DISPLAY_NAMES = {
    "USD": "American Dollar",
    "HKD": "Hong Kong Dollar",
    "GBP": "British Pound",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "SGD": "Singapore Dollar",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
    "ZAR": "South African Rand",
    "SEK": "Swedish Krona",
    "NZD": "New Zealand Dollar",
    "THB": "Thai Baht",
    "PHP": "Philippine Peso",
    "IDR": "Indonesian Rupiah",
    "EUR": "Euro",
    "KRW": "Korean Won",
    "VND": "Vietnamese Dong",
    "MYR": "Malaysian Ringgit",
    "CNY": "Chinese Yuan",
}

# 台銀網頁會對雲端主機回傳 Challenge Validation，因此無法依賴
# Chromium / ChromeDriver。改用同步台銀牌告資料的 JSON CDN，不需要 apt 套件。
link = "https://rate.bot.com.tw/xrt?Lang=en-US"
RATE_DATA_ENDPOINTS = (
    "https://cdn.jsdelivr.net/gh/haotool/app@data/public/rates/latest.json",
    "https://raw.githubusercontent.com/haotool/app/data/public/rates/latest.json",
)


def fetch_with_requests(url):
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.text


def summarize_error(exc, max_length=500):
    text = str(exc).strip().replace("\n", " ")
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def parse_currency_data_from_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    table_rows = soup.select("table.table tbody tr")
    currency_data = []

    for row in table_rows:
        tds = row.find_all("td")
        if len(tds) < 6:
            continue

        currency_text = tds[0].get_text(" ", strip=True)
        if "(" not in currency_text or ")" not in currency_text:
            continue

        current_short_name = currency_text.rsplit("(", 1)[-1].split(")", 1)[0]
        if current_short_name in {"ZAR", "SEK"}:
            continue

        cash_buy = tds[1].get_text(strip=True)
        if cash_buy in {"", "-"}:
            continue

        currency_data.append({
            "Image": contry_image_dict.get(current_short_name, ""),
            "Currency": (
                f"{CURRENCY_DISPLAY_NAMES.get(current_short_name, current_short_name)} "
                f"({current_short_name})"
            ),
            "Cash Buy": cash_buy,
        })

    return currency_data


def parse_currency_data_from_rate_data(payload):
    """Convert the mirror's details.{currency}.cash.buy data to the UI format."""
    details = payload.get("details") if isinstance(payload, dict) else None
    if not isinstance(details, dict):
        return []

    currency_data = []
    for currency_code, currency_name in CURRENCY_DISPLAY_NAMES.items():
        currency_details = details.get(currency_code)
        cash_details = (
            currency_details.get("cash")
            if isinstance(currency_details, dict)
            else None
        )
        cash_buy = cash_details.get("buy") if isinstance(cash_details, dict) else None
        if cash_buy in (None, "", "-"):
            continue

        currency_data.append({
            "Image": contry_image_dict.get(currency_code, ""),
            "Currency": f"{currency_name} ({currency_code})",
            "Cash Buy": str(cash_buy),
        })

    return currency_data


def fetch_json(url):
    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "currency-exchange-streamlit/1.0",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_exchange_rate_data():
    errors = []

    # 主要來源是同步台銀牌告匯率的 JSON CDN，完全不需要瀏覽器或 apt。
    for endpoint in RATE_DATA_ENDPOINTS:
        try:
            payload = fetch_json(endpoint)
            currency_data = parse_currency_data_from_rate_data(payload)
            if currency_data:
                update_time = payload.get("updateTime", "")
                note = "匯率資料來源：台灣銀行牌告匯率同步資料"
                if update_time:
                    note += f"（資料更新時間：{update_time}）"
                return currency_data, "Bank of Taiwan (JSON mirror)", note
            errors.append(f"JSON: {endpoint} 沒有可用的匯率資料。")
        except (requests.RequestException, ValueError, TypeError) as exc:
            errors.append(f"JSON: {summarize_error(exc)}")

    # JSON 來源暫時無法使用時，保留官方 HTML 的直接嘗試；不再啟動瀏覽器。
    try:
        raw_html = fetch_with_requests(link)
        if "Challenge Validation" not in raw_html:
            currency_data = parse_currency_data_from_html(raw_html)
            if currency_data:
                return currency_data, "Bank of Taiwan", None
            errors.append("官方頁面已回應，但沒有解析到匯率表格。")
        else:
            errors.append("官方頁面回傳驗證頁。")
    except requests.RequestException as exc:
        errors.append(f"官方頁面: {summarize_error(exc)}")

    raise RuntimeError("無法取得匯率資料。" + "；".join(errors))


try:
    with st.spinner("Loading exchange rates..."):
        currency_data, data_source, data_note = fetch_exchange_rate_data()
except requests.RequestException as exc:
    st.error(f"Unable to load exchange-rate data: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Unable to load exchange-rate data: {exc}")
    st.stop()

if data_note and hasattr(st, "toast"):
    st.toast(data_note, icon="ℹ️")

if not currency_data:
    st.error("Unable to find exchange-rate data.")
    st.stop()


# Split the data into two columns
if currency_data:
    currency_data_col1 = currency_data[:9]
    currency_data_col2 = currency_data[9:]
    
    col1, col2 = st.columns(2)
    with col1:
        for currency in currency_data_col1:
            with st.container(border=True):
                sub_col1, sub_col2, sub_col3 = st.columns([2,6.6,2.4])
                currency_short_name=0.0
                with sub_col1:
                    sub_col1.image(currency["Image"], width=100)
                with sub_col2:
                    currency_split = currency["Currency"].split("(")
                    currency_name = currency_split[0].strip()
                    currency_short_name = "(" + currency_split[1][0:3] + ")"
                    
                    st.markdown(f"<h3 style='text-align: center; color: #000000; padding: 0;'>{currency_name}</h3>", unsafe_allow_html=True)
                    st.markdown(f"<h5 style='text-align: center; color: #4c4c4c; padding: 0;'>{currency_short_name}</h5>", unsafe_allow_html=True)
                with sub_col3:
                        
                    cash_buy_adjusted = float(currency["Cash Buy"]) - float(user_currency_adjust_dict[currency_short_name[1:-1]])
                    cash_buy_adjusted = round(cash_buy_adjusted, 4)
                    st.markdown(f"<p style='text-align: center; color: #2727327; padding: 0; font-size: x-large; margin-bottom: -1rem; margin-top: 0.5rem;'>{cash_buy_adjusted}</p>", unsafe_allow_html=True)
    with col2:
        for currency in currency_data_col2:
            with st.container(border=True):
                sub_col1, sub_col2, sub_col3 = st.columns([2,6.6,2.4])
                currency_short_name=0.0
                with sub_col1:
                    sub_col1.image(currency["Image"], width=100)
                with sub_col2:
                    currency_split = currency["Currency"].split("(")
                    currency_name = currency_split[0].strip()
                    currency_short_name = "(" + currency_split[1][0:3] + ")"
                    
                    st.markdown(f"<h3 style='text-align: center; color: #000000; padding: 0;'>{currency_name}</h3>", unsafe_allow_html=True)
                    st.markdown(f"<h5 style='text-align: center; color: #4c4c4c; padding: 0;'>{currency_short_name}</h5>", unsafe_allow_html=True)
                with sub_col3:
                    cash_buy_adjusted = float(currency["Cash Buy"]) - float(user_currency_adjust_dict[currency_short_name[1:-1]])
                    cash_buy_adjusted = round(cash_buy_adjusted, 7)
                    st.markdown(f"<p style='text-align: center; color: #2727327; padding: 0; font-size: x-large; margin-bottom: -1rem; margin-top: 0.5rem;'>{cash_buy_adjusted}</p>", unsafe_allow_html=True)

