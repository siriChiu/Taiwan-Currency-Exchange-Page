import streamlit as st
from supabase import create_client, Client
import datetime as dt

# Initialize Supabase client
supabase_url = st.secrets["connections_supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections_supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

st.title("🔐 Supabase Login & Sign Up with User Config")

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

if 'currency_adjust_dict' not in st.session_state:
    st.session_state.currency_adjust_config = default_currency_adjust_config

# Initialize session state for user login status
if 'user' not in st.session_state:
    st.session_state['user'] = None
    st.session_state['token'] = None

# Display login or sign-up options based on user session
if st.session_state['user'] is None:
    login_mode = st.radio("Choose action", ["Login", "Sign Up"])

    # Sign Up Form
    if login_mode == "Sign Up":
        with st.form("signup_form"):
            name  = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            password_confirm = st.text_input("Confirm Password", type="password", key="confirm_password")
            submitted = st.form_submit_button("Create Account")

            if submitted:
                if password != password_confirm:
                    st.error("Passwords do not match!")
                else:
                    try:
                        # Sign up using Supabase
                        login_result = supabase.auth.sign_up({
                            "email": email,
                            "password": password,
                        })
                        st.success(f"Account created successfully! Please check your email for verification.")
                        # Auto login after sign up
                        login_result = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": password,
                        })
                        st.session_state['user'] = login_result.user
                        st.session_state['token'] = login_result.session.access_token
                        st.success("Logged in successfully.")
                        
                        user_id = login_result.user.id
                        token = login_result.session.access_token

                        # Fetch user subscription status from Supabase
                        user_response = supabase.auth.get_user(token)
                        user_data = user_response.user

                        # Check subscription status
                        default_user_info = {"user": name,
                                            "email": email,}
                        
                        default_subscription_info = {"registered_date": dt.datetime.now().strftime("%Y-%m-%d"),
                                                    "start_date": dt.datetime.now().strftime("%Y-%m-%d"),
                                                    "alert_date": (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d"),
                                                    "expiration_date": (dt.datetime.now() + dt.timedelta(days=60)).strftime("%Y-%m-%d"),
                                                    "status": "active",
                                                    "service_type": "monthly",
                                                    }
                        
                        supabase.table("user_configs").insert({
                            "user_id": user_id,
                            "user_info": default_user_info,
                            "subscription_info": default_subscription_info,
                            "currency_adjust_config": st.session_state.currency_adjust_config
                        }).execute()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Login Form
    if login_mode == "Login":
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

            if submitted:
                try:
                    # Login using Supabase
                    login_result = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password,
                    })
                    st.session_state['user'] = login_result.user
                    st.session_state['token'] = login_result.session.access_token
                    st.success("Logged in successfully.")


                except Exception as e:
                    st.error(f"Login failed: {e}")

# After login, allow user to customize settings
if st.session_state['user']:
    user_id = st.session_state['user'].id
    token = st.session_state['token']

    # Fetch user subscription status from Supabase
    user_response = supabase.auth.get_user(token)
    user_data = user_response.user

    st.info(f"Welcome, {st.session_state['user'].email}")

    # Fetch user config from Supabase
    headers = {"Authorization": f"Bearer {token}"}
    response = supabase.table("user_configs").select("*")\
        .eq("user_id", user_id).execute()


    if response.data:
        if 'currency_adjust_config' in response.data[0] and response.data[0]["currency_adjust_config"]:
            st.session_state.currency_adjust_config = response.data[0]["currency_adjust_config"]
            st.write(st.session_state.currency_adjust_config)

        if 'subscription_info' in response.data[0]:

            # Check subscription status
            subscription_info = response.data[0]["subscription_info"]
            if dt.datetime.now() > dt.datetime.strptime(subscription_info["expiration_date"], "%Y-%m-%d"):
                subscription_info["status"] = "expired"
                supabase.table("user_configs").update({"subscription_info": subscription_info})\
                    .eq("user_id", user_id).execute()
        else:
            st.warning("No subscription info found.")
        
        if 'user_info' not in response.data[0]:
            st.warning("No user info found.")
    else:
        st.warning("No any config found.")



    st.switch_page("pages/currency_exchange.py")

    # Update user config (theme preference)

    # if st.button("Save Config"):
    #     supabase.table("user_configs").update({"currency_adjust_config": st.session_state.currency_adjust_config})\
    #         .eq("user_id", user_id).execute()
    #     st.write(st.session_state.currency_adjust_config)
    #     st.write(default_currency_adjust_config)
    #     st.write(user_id)
    #     st.success("Configuration updated!")

    # if st.button("Logout"):
    #     st.session_state['user'] = None
    #     st.session_state['token'] = None
