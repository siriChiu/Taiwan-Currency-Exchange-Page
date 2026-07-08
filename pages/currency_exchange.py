import streamlit as st
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh
from package import browser_storage
from package import local_storage
from package import validation
st.set_page_config(
    page_title="currency exchange",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

link = "https://rate.bot.com.tw/xrt?Lang=en-US"
PLAYWRIGHT_TIMEOUT_SECONDS = 35


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


def fetch_with_playwright(url):
    import os
    import shutil
    from pathlib import Path

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    timeout_ms = int(os.environ.get(
        "BOT_PLAYWRIGHT_TIMEOUT_MS",
        PLAYWRIGHT_TIMEOUT_SECONDS * 1000,
    ))
    browser_candidates = (
        os.environ.get("CHROME_BIN"),
        os.environ.get("GOOGLE_CHROME_BIN"),
        os.environ.get("CHROMIUM_PATH"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    )
    browser_path = next(
        (path for path in browser_candidates if path and Path(path).exists()),
        None,
    )

    launch_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-crash-reporter",
        "--disable-crashpad",
    ]
    launch_options = {
        "headless": True,
        "args": launch_args,
        "timeout": timeout_ms,
    }
    if browser_path:
        launch_options["executable_path"] = browser_path

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            try:
                context = browser.new_context(
                    locale="zh-TW",
                    viewport={"width": 1280, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_selector("table.table tbody tr", timeout=timeout_ms)
                return page.content()
            finally:
                browser.close()
    except (PlaywrightError, PlaywrightTimeoutError) as exc:
        raise RuntimeError(
            f"Playwright could not load Bank of Taiwan within {timeout_ms // 1000}s: {exc}"
        ) from exc


def fetch_with_finmind():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import date, timedelta

    api_url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (date.today() - timedelta(days=14)).isoformat()
    currency_codes = [
        code
        for code in contry_image_dict
        if code not in {"ZAR", "SEK"}
    ]

    def fetch_currency(currency_code):
        response = requests.get(
            api_url,
            params={
                "dataset": "TaiwanExchangeRate",
                "data_id": currency_code,
                "start_date": start_date,
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 200 or not payload.get("data"):
            raise RuntimeError(f"FinMind returned no exchange-rate data for {currency_code}.")

        latest_rate = sorted(payload["data"], key=lambda item: item["date"])[-1]
        cash_buy = latest_rate.get("cash_buy")
        if cash_buy in (None, "", "-"):
            raise RuntimeError(f"FinMind returned no cash-buy rate for {currency_code}.")

        return currency_code, {
            "Image": contry_image_dict.get(currency_code, ""),
            "Currency": f"{CURRENCY_DISPLAY_NAMES[currency_code]} ({currency_code})",
            "Cash Buy": str(cash_buy),
        }

    rates_by_code = {}
    errors = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_code = {
            executor.submit(fetch_currency, currency_code): currency_code
            for currency_code in currency_codes
        }
        for future in as_completed(future_to_code):
            currency_code = future_to_code[future]
            try:
                code, rate = future.result()
                rates_by_code[code] = rate
            except Exception as exc:
                errors.append(f"{currency_code}: {exc}")

    if not rates_by_code:
        raise RuntimeError("Unable to load fallback exchange rates from FinMind: " + "; ".join(errors))

    return [
        rates_by_code[currency_code]
        for currency_code in currency_codes
        if currency_code in rates_by_code
    ]


@st.cache_data(ttl=14400, show_spinner=False)
def fetch_exchange_rate_data(url):
    request_error = None
    try:
        raw_html = fetch_with_requests(url)
    except requests.RequestException as exc:
        raw_html = ""
        request_error = summarize_error(exc)

    if raw_html and "Challenge Validation" not in raw_html:
        currency_data = parse_currency_data_from_html(raw_html)
        if currency_data:
            return currency_data, "Bank of Taiwan", None

    playwright_error = None
    try:
        raw_html = fetch_with_playwright(url)
        currency_data = parse_currency_data_from_html(raw_html)
        if currency_data:
            return (
                currency_data,
                "Bank of Taiwan (Playwright)",
                "台灣銀行網站回傳驗證頁，已透過 Playwright 載入台銀匯率資料。",
            )
        playwright_error = "Playwright loaded the page, but the exchange-rate table was not found."
    except Exception as exc:
        playwright_error = summarize_error(exc)

    return (
        fetch_with_finmind(),
        "FinMind",
        "台灣銀行網站目前無法直接取得匯率表格，"
        "已改用 FinMind 的台銀匯率資料。"
        f"requests：{request_error or '回傳驗證頁或未解析到表格'}；"
        f"Playwright：{playwright_error}",
    )


try:
    with st.spinner("Loading exchange rates..."):
        currency_data, data_source, data_note = fetch_exchange_rate_data(link)
except requests.RequestException as exc:
    st.error(f"Unable to load exchange-rate data: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Unable to load exchange-rate data: {exc}")
    st.stop()

if data_note:
    st.info(data_note, icon="ℹ️")

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

