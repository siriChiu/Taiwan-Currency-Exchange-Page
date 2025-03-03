# myapp.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pandas as pd

st.set_page_config(
    page_title="Scraped Currency Data",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    """<style>
    /* Style columns */
    [data-testid="stHeader"]  {
        height: 10px;
    } 
    </style>""",
)

st.html("<style> .main {overflow: hidden} </style>")


st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@100&display=swap'); 
            body * {
                font-family: 'Roboto', sans-serif !important;
                font-size: 30px;
                font-weight: 500;
                color: #091747;
            }
            </style>
            """ , unsafe_allow_html= True)

st.markdown("<h2 style='text-align: center; color: red;'>台灣銀行牌告匯率(Bank of Taiwan Exchange Rates)</h2>", unsafe_allow_html=True)

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
    currency_name = tds[0].get_text(strip=True)
# currenct_name look like "Hong Kong Dollar (HKD)Hong Kong Dollar (HKD)", remove repeated string
    current_name_remove_repeated = currency_name.split(")")[1] + ")"
    current_short_name = current_name_remove_repeated.split(" ")[-1][1:-1]
    country_image = contry_image_dict.get(current_short_name, "")

    cash_buy = tds[1].get_text(strip=True)
    cash_sell = tds[2].get_text(strip=True)
    spot_buy = tds[3].get_text(strip=True)
    spot_sell = tds[4].get_text(strip=True)

    # The link text is "查詢" in Chinese, but we'll display "Inquiry"
    forward_link = tds[5].find("a")
    forward_text = "Inquiry" if forward_link else ""

    currency_data.append({
        "Image": country_image,
        "Currency": current_name_remove_repeated,
        # "Cash Buy": cash_buy,
        "Cash Sell": cash_sell,
        # "Spot Buy": spot_buy,
        # "Spot Sell": spot_sell,
    })


# Split the data into two columns
if currency_data:
    currency_data_col1 = currency_data[:10]
    currency_data_col2 = currency_data[10:]

    col1, col2 = st.columns(2)
    with col1:
        st.data_editor(
            currency_data_col1,
            column_config={
                "Image": st.column_config.ImageColumn(
                    "Image", help="Streamlit app preview screenshots", width="small"
                ),
                "Currency": st.column_config.TextColumn(
                    "Currency",
                    help="Streamlit **widget** commands 🎈",
                    default="st.",
                    max_chars=50,
                    # width="small",
                )
            },
            hide_index=True,
            use_container_width=True,
            height = 400,
            disabled = True,
        )
    with col2:
        st.data_editor(
            currency_data_col2,
            column_config={
                "Image": st.column_config.ImageColumn(
                    "Image", help="Streamlit app preview screenshots", width="small"
                ),
                "Currency": st.column_config.TextColumn(
                    "Currency",
                    help="Streamlit **widget** commands 🎈",
                    default="st.",
                    max_chars=50,
                    # width="small",
                )
            },
            hide_index=True,
            use_container_width=True,
            height = 400,
            disabled = True,
        )

st.link_button("#### 台灣銀行牌告匯率(Bank of Taiwan Exchange Rates)", "https://rate.bot.com.tw/xrt?Lang=zh-TW")
