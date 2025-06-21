import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="APIHub Assistant", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Chatbot", "Dashboard"])

if page == "Chatbot":
    st.switch_page("pages/1_Chatbot.py")
elif page == "Dashboard":
    st.switch_page("pages/2_Dashboard.py")
