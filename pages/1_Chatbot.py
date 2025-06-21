import os
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from twilio.rest import Client
from datetime import datetime, timedelta, timezone

from langchain.chat_models import init_chat_model
from langchain.schema.messages import AIMessage, HumanMessage, SystemMessage


load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_NUMBER")
support_number = os.getenv("SUPPORT_PHONE_NUMBER")
mongo_uri = os.getenv("MONGODB_URI")


groq_api_key = st.secrets["GROQ_API_KEY"]
twilio_sid = st.secrets["TWILIO_ACCOUNT_SID"]
twilio_token = st.secrets["TWILIO_AUTH_TOKEN"]
twilio_number = st.secrets["TWILIO_NUMBER"]
support_number = st.secrets["SUPPORT_PHONE_NUMBER"]
mongo_uri = st.secrets["MONGODB_URI"]


if not support_number:
    st.error("SUPPORT_PHONE_NUMBER environment variable not set.")
    st.stop()


client = MongoClient(mongo_uri)
db = client["apiman"]
tickets = db["support_tickets"]
logs = db["api_usage_logs"]


chat_model = init_chat_model(
    model="llama3-8b-8192",
    model_provider="groq",
    api_key=groq_api_key,
    temperature=0
)


def send_whatsapp(ticket_id, message):
    try:
        client = Client(twilio_sid, twilio_token)
        client.messages.create(
            body=f"Support Ticket #{ticket_id}\n{message}",
            from_="whatsapp:" + twilio_number,
            to="whatsapp:" + support_number
        )
    except Exception as e:
        st.warning(f"Failed to send WhatsApp message: {e}")


def create_ticket(query, contact="anonymous"):
    ticket = {
        "query": query,
        "contact": contact,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = tickets.insert_one(ticket)
    send_whatsapp(str(result.inserted_id), query)
    return str(result.inserted_id)


SYSTEM_PROMPT = """
You are APIMAN, a chatbot for APIHub. Only answer APIHub-related questions about:
- Endpoints
- Authentication (keys, tokens)
- Rate limits
- Errors
- Data formats

If the question is off-topic or unclear, say: 
"I cannot resolve this. A support ticket will be created."
"""


st.title("APIHub Chat Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


with st.expander("Create Ticket Manually"):
    with st.form("ticket_form"):
        subject = st.text_input("Subject")
        details = st.text_area("Full Description")
        contact = st.text_input("Contact (email or username)")
        submitted = st.form_submit_button("Submit Ticket")
        if submitted and (subject or details):
            full_text = f"{subject} - {details}"
            tid = create_ticket(full_text, contact or "anonymous")
            st.success(f"Ticket #{tid} created successfully.")


user_input = st.chat_input("Ask about APIHub...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    try:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + [
            HumanMessage(content=msg["content"]) if msg["role"] == "user" else AIMessage(content=msg["content"])
            for msg in st.session_state.chat_history[-5:]
        ]
        messages.append(HumanMessage(content=user_input))
        response = chat_model.invoke(messages).content

       
        trigger_phrases = [
            "i cannot resolve this",
            "off-topic",
            "not related",
            "i'm not sure",
            "contact support",
            "ticket will be created",
        ]
        needs_ticket = any(phrase in response.lower() for phrase in trigger_phrases)

        if needs_ticket:
            tid = create_ticket(user_input)
            response += f"\n\nSupport Ticket #{tid} has been automatically created."

        st.session_state.chat_history.append({"role": "assistant", "content": response})

    except Exception as e:
        tid = create_ticket(user_input)
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"Bot failed. Ticket #{tid} created."
        })


for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

