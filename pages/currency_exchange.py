import datetime
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

if 'user' not in st.session_state or 'token' not in st.session_state:
    st.switch_page("main.py")

user_id = st.session_state['user'].id

try:
    latest_subscription = validation.get_subscription_info()
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
        "⛔ 您的訂閱已到期，無法繼續使用。\n\n"
        f"到期日：{_sub_status['sub']['expiration_date']}\n\n"
        "請聯絡管理員續訂。",
        icon="🔒",
    )
    st.stop()
elif _sub_status["near_expiry"]:
    days = _sub_status["days_left"]
    expiry_date = _sub_status["sub"]["expiration_date"]
    st.warning(
        f"⚠️ 您的訂閱將在 **{days} 天後**（{expiry_date}）到期，請儘早聯絡管理員續訂。",
        icon="⚠️",
    )
# ─────────────────────────────────────────────────────────────────────────────

if 'currency_adjust_config' not in st.session_state:
    st.session_state['currency_adjust_config'] = {
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

st.session_state['currency_adjust_config'] = browser_storage.get_json(
    "currency_adjust_config",
    st.session_state['currency_adjust_config'],
)

user_currency_adjust_dict = dict(st.session_state['currency_adjust_config'])

with st.sidebar:
    with st.expander("設定",icon="⚙️", expanded=True):
        # st.write("螢幕方向")
        # st.radio("螢幕方向", ["橫向", "直向"], index=0, key="screen_side", label_visibility="collapsed")

        st.write("校正匯率")
        with st.form(key="form"):
            for key, value in user_currency_adjust_dict.items():
                column1, column2 = st.columns([1, 3])
                with column1:
                    st.write(key)
                with column2:
                    user_currency_adjust_dict[key] = st.number_input(key, value=value, step=0.000001, format="%.6f", label_visibility="collapsed")

            submit_button = st.form_submit_button(label="確定", type="primary")
            if submit_button:
                browser_storage.set_json("currency_adjust_config", user_currency_adjust_dict)
                st.session_state['currency_adjust_config'] = dict(user_currency_adjust_dict)
                st.success("已儲存到此瀏覽器的個人匯率設定")
        

        # if st.button("Logout"):
        #     st.session_state['user'] = None
        #     st.session_state['token'] = None
        #     st.switch_page("main.py")


count = st_autorefresh(interval=10800000, key="parseCurrencyRate") # refresh every 3 hours

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
    
_, col_refresh = st.columns([7, 3])
with col_refresh:
    last_update_time = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")
    if st.button(f"🔄 Rrefresh time: {last_update_time}", type='tertiary',use_container_width= True):
        st.rerun()

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

link = "https://rate.bot.com.tw/xrt/all/day?Lang=en-US"
f = requests.get(link)
raw_html = f.text

# Parse the HTML with BeautifulSoup
soup = BeautifulSoup(raw_html, "html.parser")

# Locate table rows
table_rows = soup.select("table.table tbody tr")

# Prepare a list of dicts for each row
currency_data = []

for row in table_rows:
    tds = row.find_all("td")
    if len(tds) < 6:
        continue
    
    # tds[0]: 幣別 (Currency Name)
    # tds[1]: 現金買入 (Cash Buy)
    # tds[2]: 現金賣出 (Cash Sell)
    # tds[3]: 即期買入 (Spot Buy)
    # tds[4]: 即期賣出 (Spot Sell)
    # tds[5]: 遠期匯率 link
    currency_short_name = tds[0].get_text(strip=True)
    current_name_remove_repeated = currency_short_name.split(")")[1] + ")"
    current_short_name = current_name_remove_repeated.split(" ")[-1][1:-1]
    country_image = contry_image_dict.get(current_short_name, "")

    cash_buy = tds[1].get_text(strip=True)
    cash_sell = tds[2].get_text(strip=True)
    spot_buy = tds[3].get_text(strip=True)
    spot_sell = tds[4].get_text(strip=True)

    # The link text is "查詢" in Chinese, but we'll display "Inquiry"
    forward_link = tds[5].find("a")
    forward_text = "Inquiry" if forward_link else ""
    
    if current_short_name == "ZAR" or current_short_name == "SEK":
        continue

    currency_data.append({
        "Image": country_image,
        "Currency": current_name_remove_repeated,
        "Cash Buy": cash_buy,
    })


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
                    cash_buy_adjusted = round(cash_buy_adjusted, 4)
                    st.markdown(f"<p style='text-align: center; color: #2727327; padding: 0; font-size: x-large; margin-bottom: -1rem; margin-top: 0.5rem;'>{cash_buy_adjusted}</p>", unsafe_allow_html=True)

