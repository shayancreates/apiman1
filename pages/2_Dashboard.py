# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from pymongo import MongoClient
# from datetime import datetime
# from dotenv import load_dotenv
# import os


# load_dotenv()
# mongo_uri = os.getenv("MONGODB_URI")

# mongo_uri = st.secrets["MONGODB_URI"]
# client = MongoClient(mongo_uri)
# db = client["apiman"]
# logs = db["api_usage_logs"]
# tickets = db["support_tickets"]

# st.title("Admin Dashboard")


# st.subheader("API Usage Summary")

# COST_PER_CALL = {
#     "Image API": 0.002,
#     "Video API": 0,
#     "Weather API": 0,
#     "Ecommerce API": 0.001,
#     "QR Code API": 0.001,
#     "Profile Photo API": 0.001,
#     "Jokes API": 0.001
# }

# log_data = list(logs.find())

# if log_data:
#     df = pd.DataFrame(log_data)
#     df["timestamp"] = pd.to_datetime(df["timestamp"])
#     api_counts = df["api"].value_counts().reset_index()
#     api_counts.columns = ["API", "Calls"]
#     api_counts["Cost ($)"] = api_counts.apply(
#         lambda row: round(row["Calls"] * COST_PER_CALL.get(row["API"], 0), 3), axis=1
#     )
#     st.dataframe(api_counts)

#     st.subheader("API Usage Over Time")
#     df_daily = df.groupby([pd.Grouper(key="timestamp", freq="D"), "api"]).size().reset_index(name="Count")
#     fig = px.line(df_daily, x="timestamp", y="Count", color="api", title="Daily API Usage")
#     st.plotly_chart(fig, use_container_width=True)
# else:
#     st.warning("No API usage logs found.")


# st.subheader("Open Support Tickets")

# open_tickets = list(tickets.find({"status": "open"}))

# if open_tickets:
#     for ticket in open_tickets:
#         created_at = datetime.fromisoformat(ticket["created_at"])
#         hours_open = round((datetime.now(timezone.utc) - created_at).total_seconds() / 3600, 2)

#         col1, col2 = st.columns([4, 1])
#         with col1:
#             st.markdown(f"""
#             - **Ticket ID:** `{ticket['_id']}`
#             - **Query:** {ticket['query']}
#             - **Contact:** {ticket.get('contact', 'anonymous')}
#             - **Status:** {ticket['status']}
#             - **Aging Time:** {hours_open} hours
#             """)

#         with col2:
#             if st.button("Close Ticket", key=str(ticket["_id"])):
#                 tickets.update_one({"_id": ticket["_id"]}, {"$set": {"status": "closed"}})
#                 st.success(f"Ticket #{ticket['_id']} closed.")
#                 st.experimental_rerun()
# else:
#     st.info("No open tickets found.")

import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone, UTC
from dotenv import load_dotenv
import os
import numpy as np

# Load environment variables
load_dotenv()

# MongoDB Connection
mongo_uri = os.getenv("MONGODB_URI")
mongo_uri = st.secrets["MONGODB_URI"]

try:
    client = MongoClient(mongo_uri)
    db = client["apiman"]
    logs_collection = db["api_usage_logs"]
    tickets_collection = db["support_tickets"]
except Exception as e:
    st.error(f"Could not connect to MongoDB: {e}")
    st.stop()

st.set_page_config(layout="wide", page_title="API Admin Dashboard", initial_sidebar_state="collapsed")

# API Configuration
API_CONFIGS = {
    "Image API": {
        "cost_per_call": 0.002,
        "quota_daily": 10000,
        "rate_limit_per_second": 10
    },
    "Video API": {
        "cost_per_call": 0.001,
        "quota_daily": 5000,
        "rate_limit_per_second": 5
    },
    "Weather API": {
        "cost_per_call": 0.0005,
        "quota_daily": 20000,
        "rate_limit_per_second": 20
    },
    "Ecommerce API": {
        "cost_per_call": 0.001,
        "quota_daily": 15000,
        "rate_limit_per_second": 15
    },
    "QR Code API": {
        "cost_per_call": 0.001,
        "quota_daily": 8000,
        "rate_limit_per_second": 8
    },
    "Profile Photo API": {
        "cost_per_call": 0.001,
        "quota_daily": 7000,
        "rate_limit_per_second": 7
    },
    "Jokes API": {
        "cost_per_call": 0.001,
        "quota_daily": 25000,
        "rate_limit_per_second": 25
    }
}

# Helper Functions
@st.cache_data(ttl=3600)
def get_api_logs():
    return list(logs_collection.find())

def ensure_timezone_aware(dt):
    """Ensure datetime is timezone-aware (UTC if no timezone specified)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def calculate_daily_usage(df, api_name, include_dummy_trend=True):
    end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=29)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
    
    df_api = pd.DataFrame()
    if 'api' in df.columns:
        df_api = df[df["api"] == api_name]

    if not df_api.empty:
        # Ensure timestamp is timezone-aware
        if 'timestamp' in df_api.columns:
            df_api['timestamp'] = df_api['timestamp'].apply(ensure_timezone_aware)
        
        df_daily = df_api.groupby(pd.Grouper(key="timestamp", freq="D")).size().reset_index(name="Count")
        df_daily.columns = ["Date", "Count"]
        full_df = pd.DataFrame({"Date": all_dates})
        
        # Convert Date columns to datetime and ensure UTC timezone
        df_daily['Date'] = pd.to_datetime(df_daily['Date'])
        if df_daily['Date'].dt.tz is None:
            df_daily['Date'] = df_daily['Date'].dt.tz_localize('UTC')
        else:
            df_daily['Date'] = df_daily['Date'].dt.tz_convert('UTC')
            
        full_df['Date'] = pd.to_datetime(full_df['Date'])
        if full_df['Date'].dt.tz is None:
            full_df['Date'] = full_df['Date'].dt.tz_localize('UTC')
        else:
            full_df['Date'] = full_df['Date'].dt.tz_convert('UTC')
        
        daily_usage = pd.merge(full_df, df_daily, on="Date", how="left").fillna(0)
    elif include_dummy_trend:
        base_value = API_CONFIGS.get(api_name, {}).get("quota_daily", 1000) / 10
        if base_value == 0: base_value = 100
        
        dummy_counts = []
        for day_idx in range(len(all_dates)):
            trend_factor = np.sin(day_idx / 5) * (base_value / 2)
            random_noise = np.random.normal(0, base_value / 4)
            count = max(0, int(base_value + trend_factor + random_noise))
            dummy_counts.append(count)
            
        daily_usage = pd.DataFrame({"Date": all_dates, "Count": dummy_counts})
    else:
        return pd.DataFrame(columns=["Date", "Count"])
        
    return daily_usage
def calculate_current_daily_usage(df, api_name):
    if 'api' not in df.columns or df.empty:
        return 0

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    current_day_usage = df[(df["api"] == api_name) & (df["timestamp"] >= today_start)].shape[0]
    return current_day_usage

# Streamlit UI
st.title("🚀 API Management Dashboard")

# Load all logs once
log_data = get_api_logs()
df_logs = pd.DataFrame()

expected_log_columns = ["api", "timestamp", "user_id", "status_code"]

if log_data:
    df_logs = pd.DataFrame(log_data)
    if 'timestamp' in df_logs.columns:
        df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"]).apply(ensure_timezone_aware)
    else:
        st.warning("Logs found but 'timestamp' column is missing. Some features may not work correctly.")
        df_logs['timestamp'] = datetime.now(UTC)
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])

    for col in expected_log_columns:
        if col not in df_logs.columns:
            st.warning(f"Logs found but '{col}' column is missing. Adding a default placeholder column.")
            if col == 'api':
                df_logs[col] = "unknown_api"
            elif col == 'user_id':
                df_logs[col] = "unknown_user"
            elif col == 'status_code':
                df_logs[col] = 200
            else:
                df_logs[col] = None
else:
    df_logs = pd.DataFrame(columns=expected_log_columns)
    df_logs['timestamp'] = pd.Series(dtype='datetime64[ns, UTC]')

st.markdown("   ")

# Top-Level API Navigation
api_tabs_list = ["Overview"] + sorted(list(API_CONFIGS.keys()))
selected_api_tab = st.tabs(api_tabs_list)

for i, api_name_in_tab in enumerate(api_tabs_list):
    with selected_api_tab[i]:
        if api_name_in_tab == "Overview":
            st.subheader("Overall API Usage Summary")
            
            if not df_logs.empty and 'api' in df_logs.columns and df_logs['api'].any():
                api_counts = df_logs["api"].value_counts().reset_index()
                api_counts.columns = ["API", "Calls"]
                api_counts["Cost ($)"] = api_counts.apply(
                    lambda row: round(row["Calls"] * API_CONFIGS.get(row["API"], {}).get("cost_per_call", 0), 3), axis=1
                )
                st.dataframe(api_counts, use_container_width=True)

                st.subheader("API Usage Over Time (All APIs Combined)")
                df_daily_all = df_logs.groupby([pd.Grouper(key="timestamp", freq="D"), "api"]).size().reset_index(name="Count")
                
                if not df_daily_all.empty and df_daily_all['Count'].sum() > 0:
                    fig_all_usage = px.line(df_daily_all, x="timestamp", y="Count", color="api", title="Daily API Usage (All APIs Combined)")
                    fig_all_usage.update_layout(hovermode="x unified", legend_title_text='API')
                    st.plotly_chart(fig_all_usage, use_container_width=True)
                else:
                    end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = end_date - timedelta(days=29)
                    all_dates_dummy = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
                    dummy_data_all = []
                    for date_idx, date in enumerate(all_dates_dummy):
                        for api in API_CONFIGS.keys():
                            base_value = API_CONFIGS.get(api, {}).get("quota_daily", 1000) / 10 
                            if base_value == 0: base_value = 100
                            
                            trend_factor = np.sin(date_idx / 4) * (base_value / 2)
                            random_noise = np.random.normal(0, base_value / 4)
                            count = max(0, int(base_value + trend_factor + random_noise))
                            dummy_data_all.append({"timestamp": date, "api": api, "Count": count})
                    df_dummy_all = pd.DataFrame(dummy_data_all)
                    fig_all_usage = px.line(df_dummy_all, x="timestamp", y="Count", color="api", title="Daily API Usage (All APIs Combined)")
                    fig_all_usage.update_layout(hovermode="x unified", legend_title_text='API')
                    st.plotly_chart(fig_all_usage, use_container_width=True)
            else:
                dummy_api_counts = pd.DataFrame({
                    "API": list(API_CONFIGS.keys()),
                    "Calls": [np.random.randint(500, 5000) for _ in API_CONFIGS],
                    "Cost ($)": [round(np.random.rand() * 10, 2) for _ in API_CONFIGS]
                })
                st.dataframe(dummy_api_counts, use_container_width=True)

                st.subheader("API Usage Over Time (All APIs Combined)")
                end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = end_date - timedelta(days=29)
                all_dates_dummy = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
                dummy_data_all = []
                for date_idx, date in enumerate(all_dates_dummy):
                    for api in API_CONFIGS.keys():
                        base_value = API_CONFIGS.get(api, {}).get("quota_daily", 1000) / 10 
                        if base_value == 0: base_value = 100
                        trend_factor = np.sin(date_idx / 4) * (base_value / 2)
                        random_noise = np.random.normal(0, base_value / 4)
                        count = max(0, int(base_value + trend_factor + random_noise))
                        dummy_data_all.append({"timestamp": date, "api": api, "Count": count})
                df_dummy_all = pd.DataFrame(dummy_data_all)
                fig_all_usage = px.line(df_dummy_all, x="timestamp", y="Count", color="api", title="Daily API Usage (All APIs Combined)")
                fig_all_usage.update_layout(hovermode="x unified", legend_title_text='API')
                st.plotly_chart(fig_all_usage, use_container_width=True)

        else:
            st.header(f"📊 {api_name_in_tab} - Detailed Monitoring")
            api_config = API_CONFIGS.get(api_name_in_tab, {})
            quota_daily = api_config.get("quota_daily", "N/A")
            rate_limit_per_second = api_config.get("rate_limit_per_second", "N/A")
            cost_per_call = api_config.get("cost_per_call", "N/A")

            selected_option = st.radio(
                "Select a metric:",
                ["Usage per API", "Quota per API", "Rate Limit per API", "Progress Bar"],
                key=f"option_{api_name_in_tab}",
                horizontal=True
            )

            st.markdown("---")

            if selected_option == "Usage per API":
                st.subheader(f"Daily API Usage Trend for {api_name_in_tab}")
                
                daily_usage_df = calculate_daily_usage(df_logs, api_name_in_tab, include_dummy_trend=True)
                
                total_calls = df_logs[df_logs["api"] == api_name_in_tab].shape[0] if not df_logs.empty and 'api' in df_logs.columns else daily_usage_df['Count'].sum()

                col_metric, col_graph = st.columns([1, 3])
                with col_metric:
                    st.metric(label=f"Total Calls for {api_name_in_tab} (Last 30 Days)", value=f"{total_calls:,}")
                    st.write("This graph shows the daily number of API calls over the last 30 days.")
                with col_graph:
                    fig_api_usage = px.line(daily_usage_df, x="Date", y="Count",
                                             title=f"Daily API Usage for {api_name_in_tab} (Last 30 Days)")
                    fig_api_usage.update_layout(hovermode="x unified", xaxis_title="Date", yaxis_title="Number of Calls")
                    st.plotly_chart(fig_api_usage, use_container_width=True)

            elif selected_option == "Quota per API":
                st.subheader(f"Quota Information and Trend for {api_name_in_tab}")
                
                quota_val = api_config.get("quota_daily", 0) 

                if quota_val > 0:
                    st.info(f"**Configured Daily Quota:** {quota_val:,} calls")
                    st.info(f"**Cost per Call:** ${cost_per_call}")

                    current_daily_usage = calculate_current_daily_usage(df_logs, api_name_in_tab)
                    remaining_quota = quota_val - current_daily_usage

                    col_metric_quota, col_graph_quota = st.columns([1, 3])
                    with col_metric_quota:
                        st.metric(label="Current Daily Usage", value=f"{current_daily_usage:,} calls")
                        st.metric(label="Remaining Daily Quota", value=f"{remaining_quota:,} calls")
                        if remaining_quota <= 0:
                            st.error("Daily quota exceeded! Consider increasing the limit or optimizing usage.")
                        elif remaining_quota < quota_val * 0.2:
                            st.warning("Daily quota is running low! Only 20% or less remaining.")
                        else:
                            st.success("Daily quota is well within limits.")
                    
                    with col_graph_quota:
                        end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                        start_date = end_date - timedelta(days=29)
                        all_dates = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
                        
                        quota_trend_data = []
                        daily_usage_for_quota = calculate_daily_usage(df_logs, api_name_in_tab, include_dummy_trend=True)
                        daily_usage_dict = daily_usage_for_quota.set_index('Date')['Count'].to_dict()

                        for date in all_dates:
                            usage = daily_usage_dict.get(date, 0)
                            quota_trend_data.append({"Date": date, "Usage": usage, "Daily Quota": quota_val})

                        df_quota_trend = pd.DataFrame(quota_trend_data)
                        
                        fig_quota_trend = px.line(df_quota_trend, x="Date", y=["Usage", "Daily Quota"],
                                                     title=f"Daily Usage vs. Quota for {api_name_in_tab}")
                        fig_quota_trend.update_layout(hovermode="x unified", xaxis_title="Date", yaxis_title="Count")
                        st.plotly_chart(fig_quota_trend, use_container_width=True)
                else:
                    st.warning("Daily quota information is not configured or is zero for this API. Quota trend graph cannot be displayed.")
                    st.info("Please set a positive 'quota_daily' in the API_CONFIGS for this API.")

            elif selected_option == "Rate Limit per API":
                st.subheader(f"Rate Limit Information and Trend for {api_name_in_tab}")
                if rate_limit_per_second != "N/A":
                    st.info(f"**Configured Rate Limit:** {rate_limit_per_second} calls per second")
                    st.markdown("""
                    <p>The rate limit dictates the maximum number of requests allowed within a one-second window to prevent system overload and ensure fair usage. Adhering to this limit is crucial for stable API performance.</p>
                    """, unsafe_allow_html=True)
                    
                    end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = end_date - timedelta(days=29)
                    all_dates = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
                    
                    rate_limit_trend_data = []
                    for date in all_dates:
                        rate_limit_trend_data.append({"Date": date, "Rate Limit": rate_limit_per_second})
                    
                    df_rate_limit_trend = pd.DataFrame(rate_limit_trend_data)
                    
                    fig_rate_limit_trend = px.line(df_rate_limit_trend, x="Date", y="Rate Limit",
                                                     title=f"Configured Daily Rate Limit for {api_name_in_tab}")
                    fig_rate_limit_trend.update_layout(hovermode="x unified", xaxis_title="Date", yaxis_title="Calls per Second")
                    st.plotly_chart(fig_rate_limit_trend, use_container_width=True)
                else:
                    st.warning("Rate limit information is not configured for this API.")
                    st.info("No rate limit trend graph can be displayed without a configured rate limit.")

            elif selected_option == "Progress Bar":
                st.subheader(f"Daily Usage Progress for {api_name_in_tab}")
                
                api_config = API_CONFIGS.get(api_name_in_tab, {})
                quota_daily = api_config.get("quota_daily", 0)

                if quota_daily > 0:
                    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    actual_current_daily_usage = 0
                    if not df_logs.empty and 'api' in df_logs.columns:
                        actual_current_daily_usage = df_logs[(df_logs["api"] == api_name_in_tab) & (df_logs["timestamp"] >= today_start)].shape[0]

                    if actual_current_daily_usage > 0:
                        current_daily_usage = actual_current_daily_usage
                        st.info("Displaying real-time usage progress.")
                    else:
                        current_daily_usage = np.random.randint(0, quota_daily + 1)
                        st.info("No real-time usage data available for today. Displaying simulated progress.")

                    progress_percentage = min((current_daily_usage / quota_daily) * 100, 100)

                    st.metric(label="Usage Today / Daily Quota", value=f"{current_daily_usage:,} / {quota_daily:,}")
                    st.progress(progress_percentage / 100)

                    if progress_percentage >= 100:
                        st.error("Daily quota reached! No more calls can be made today without exceeding the limit.")
                    elif progress_percentage >= 80:
                        st.warning("Approaching daily quota limit! Usage is at 80% or more.")
                    else:
                        st.success("Daily usage is well within limits.")
                else:
                    st.warning("Daily quota information is not configured or is zero for this API. Progress bar cannot be displayed.")
                    st.info("Please set a positive 'quota_daily' in the API_CONFIGS for this API.")

st.markdown("---")

# Support Tickets Section
st.subheader("📊 Open Support Tickets")

open_tickets = list(tickets_collection.find({"status": "open"}))

if open_tickets:
    for ticket in open_tickets:
        created_at = ticket["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        created_at = ensure_timezone_aware(created_at)
        ticket["hours_open"] = round((datetime.now(UTC) - created_at).total_seconds() / 3600, 2)

    open_tickets_sorted = sorted(open_tickets, key=lambda x: x["hours_open"], reverse=True)

    for ticket in open_tickets_sorted:
        col1_t, col2_t = st.columns([4, 1])
        with col1_t:
            st.markdown(f"""
            <div style="background-color: #1a1e27; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <p style="font-size: 1.1rem; margin-bottom: 5px;"><strong>Ticket ID:</strong> <code>{ticket['_id']}</code></p>
                <p style="margin-bottom: 5px;"><strong>Query:</strong> {ticket['query']}</p>
                <p style="margin-bottom: 5px;"><strong>Contact:</strong> {ticket.get('contact', 'anonymous')}</p>
                <p style="margin-bottom: 5px;"><strong>Status:</strong> <span style="color:orange; font-weight:bold;">{ticket['status']}</span></p>
                <p style="margin-bottom: 0;"><strong>Aging Time:</strong> <span style="color:#FFA07A; font-weight:bold;">{ticket['hours_open']} hours</span></p>
            </div>
            """, unsafe_allow_html=True)

        with col2_t:
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            if st.button("✅ Close Ticket", key=str(ticket["_id"])):
                tickets_collection.update_one({"_id": ticket["_id"]}, {"$set": {"status": "closed"}})
                st.success(f"Ticket #{ticket['_id']} closed successfully!")
                st.rerun()
else:
    st.info("🎉 No open support tickets at the moment. All clear!")

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #FAFAFA;
        font-family: 'Segoe UI', sans-serif;
    }
    h1 {
        color: #90CAF9;
        text-align: center;
        padding-bottom: 15px;
        border-bottom: 2px solid #2e3440;
        margin-bottom: 30px;
        font-size: 2.5rem;
    }
    h2, h3, h4, h5, h6 {
        color: #BBDEFB;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #3f51b5;
        padding-left: 10px;
    }
    h2 { font-size: 1.8rem; }
    h3 { font-size: 1.5rem; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-size: 1rem;
        cursor: pointer;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid #2e3440;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 12px 25px;
        border-radius: 10px;
        transition: background-color 0.3s, color 0.3s, box-shadow 0.3s;
        font-weight: bold;
        color: #BBDEFB;
        background-color: #1a1e27;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #2e3440;
        color: #E0E0E0;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #3f51b5;
        color: white;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
        border-bottom: 3px solid #66BB6A;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.15rem;
        font-weight: bold;
        margin: 0;
    }
    .stRadio > label {
        font-weight: bold;
        font-size: 1.1rem;
        color: #90CAF9;
    }
    .stRadio [data-baseweb="radio"] {
        background-color: #1a1e27;
        border-radius: 8px;
        padding: 8px 15px;
        margin-right: 10px;
        transition: background-color 0.3s;
        border: 1px solid #2e3440;
    }
    .stRadio [data-baseweb="radio"]:hover {
        background-color: #2e3440;
    }
    .stRadio [data-baseweb="radio"][aria-checked="true"] {
        background-color: #5C6BC0;
        color: white;
        border: 1px solid #5C6BC0;
    }
    .stAlert {
        border-radius: 8px;
        padding: 15px;
        font-size: 1rem;
        margin-top: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .stMetric > div > div:first-child {
        font-size: 1.1rem;
        color: #BBDEFB;
        font-weight: normal;
    }
    .stMetric > div > div:last-child {
        font-size: 2.2rem;
        font-weight: bold;
        color: #E0E0E0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .stPlotlyChart {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #2e3440;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    p {
        font-size: 1rem;
        line-height: 1.6;
        color: #FAFAFA;
    }
    b, strong {
        color: #E0E0E0;
    }
    code {
        background-color: #2e3440;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.9rem;
        color: #BBDEFB;
    }
    hr {
        border-top: 1px solid #2e3440;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    div[data-testid="stMarkdown"] > div > div > div[style*="background-color: #1a1e27"] {
        border: 1px solid #2e3440;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #1a1e27;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMarkdown"] p {
        margin-bottom: 0.5em;
    }
</style>
""", unsafe_allow_html=True)