import os

import requests
import streamlit as st

# ---------- Configuration (read from the .env file passed in by Docker Compose) ----------
API_URL = os.getenv("BASE_URL", "http://api:5001")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODELS = {
    "NVIDIA Nemotron 3 Ultra (free)": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "Other (type a model ID)": None,
}


def check_backend():
    """Call the API's /ping route and return True if it answers 'pong'."""
    try:
        response = requests.get(f"{API_URL}/ping", timeout=5)
        return response.ok and response.json().get("ack") == "pong"
    except requests.RequestException:
        return False


def ask_model(question, model_id):
    """Send the question to the API's /chat route and return the model's answer."""
    response = requests.get(
        f"{API_URL}/chat",
        params={
            "model_id": model_id,
            "openrouter_token": OPENROUTER_API_KEY,
            "input": question,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("ack", "")


# ---------- Page setup ----------
st.set_page_config(page_title="Text Completion System", page_icon="💬")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Sidebar: settings ----------
with st.sidebar:
    st.header("Settings")

    model_label = st.selectbox("Language model", list(MODELS.keys()))
    model_id = MODELS[model_label]
    if model_id is None:
        model_id = st.text_input(
            "OpenRouter model ID", placeholder="e.g. provider/model-name:free"
        ).strip()
    st.caption(f"Using: `{model_id or 'no model selected'}`")

    st.divider()

    st.subheader("Backend status")
    if st.button("Check connection"):
        if check_backend():
            st.success("Backend is online")
        else:
            st.error(f"Cannot reach the backend at {API_URL}")

    if not OPENROUTER_API_KEY:
        st.warning("No OpenRouter API key found. Add it to the .env file.")

    st.divider()

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# ---------- Main area: conversation ----------
st.title("💬 Text Completion System")
st.caption(
    "Type a question below. Your message is sent to the backend API, "
    "which asks the language model and returns the answer."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Ask me something")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if not OPENROUTER_API_KEY:
            answer = "No API key is set, so I can't call the model. Check the .env file."
            st.error(answer)
        elif not model_id:
            answer = "Please choose a model or type a model ID in the sidebar."
            st.error(answer)
        else:
            try:
                with st.spinner(f"Asking {model_id}..."):
                    answer = ask_model(question, model_id)
                st.markdown(answer)
            except requests.Timeout:
                answer = "The model took too long to answer. Please try again."
                st.error(answer)
            except requests.ConnectionError:
                answer = f"Cannot reach the backend at {API_URL}. Is the API container running?"
                st.error(answer)
            except requests.HTTPError as error:
                answer = (
                    f"The backend returned an error ({error.response.status_code}). "
                    "Check the API key and the model ID."
                )
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})