import datetime
import streamlit as st
import requests
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Scraped Currency Data",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

currency_adjust_dict = {
    "USD": 1.3,
    "HKD": 0.15,
    "GBP": 1.5,
    "AUD": 1.2,
    "CAD": 1.2,
    "SGD": 1.2,
    "CHF": 1.3,
    "JPY": 0.012,
    "ZAR": 0,
    "SEK": 0,
    "NZD": 1.2,
    "THB": 0.05,
    "PHP": 0.05,
    "IDR": 0,
    "EUR": 1.5,
    "KRW": 0.0012,
    "VND": 0.0005,
    "MYR": 0.5,
    "CNY": 0.25
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
                        
                    cash_buy_adjusted = float(currency["Cash Buy"]) - float(currency_adjust_dict[currency_short_name[1:-1]])
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
                    cash_buy_adjusted = float(currency["Cash Buy"]) - float(currency_adjust_dict[currency_short_name[1:-1]])
                    cash_buy_adjusted = round(cash_buy_adjusted, 4)
                    st.markdown(f"<p style='text-align: center; color: #2727327; padding: 0; font-size: x-large; margin-bottom: -1rem; margin-top: 0.5rem;'>{cash_buy_adjusted}</p>", unsafe_allow_html=True)

