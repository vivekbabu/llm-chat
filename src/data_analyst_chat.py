import pandas as pd
import streamlit as st

from streamlit_chat import message
from bot_init import get_text, sidebar
from large_language_model_utilities import interact_with_data_api


def chat_with_data():

    st.set_page_config(page_title="Data Explorer", page_icon="🔍")
    st.title("🔍 Data Explorer: Query, Analyze, and Visualize Your Data")

    with st.sidebar:
        model_params = sidebar()
        memory_window = st.slider(
            label="Memory Window",
            value=3,
            min_value=1,
            max_value=10,
            step=1,
            help=(
               """The number of past chat interactions retained for context. For example, setting this to 3 will keep the last three pairs of prompts and responses, meaning the last 6 messages in the chat history."""
            )
        )

    uploaded_file = st.file_uploader(label="Please Upload A File", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        # Seed the system prompts
        prompt = f"""You are a python expert. You will be given questions for manipulating an input dataframe. The available columns are: `{df.columns}`. Use them for extracting the relevant data. """
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "system", "content": prompt}]
    else:
        df = pd.DataFrame([])

    # Storing the chat
    if "generated" not in st.session_state:
        st.session_state["generated"] = ["Please upload your data"]

    if "past" not in st.session_state:
        st.session_state["past"] = []

    if ("messages" in st.session_state) and \
            (len(st.session_state["messages"]) > 2 * memory_window):
        # Keep only the system prompt and the last `memory_window` prompts/answers
        st.session_state["messages"] = (
            # the first one is always the system prompt
            [st.session_state["messages"][0]]
            + st.session_state["messages"][-(2 * memory_window - 2):]
        )

    if 'messages' in st.session_state:
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

    input_from_user = get_text()

    if ((len(st.session_state["past"]) > 0)
            and (input_from_user == st.session_state["past"][-1])):
        input_from_user = ""

    if input_from_user:
        if df.empty:
            st.warning("The dataframe is empty. Please upload a valid file.", icon="🚫")
        else:
            st.session_state["messages"].append({"role": "user", "content": input_from_user})
            st.chat_message('user').write(input_from_user)
            response = interact_with_data_api(df, **model_params)
            st.session_state.past.append(input_from_user)
            if response is not None:
                st.session_state.generated.append(response)
                st.session_state["messages"].append(
                    {"role": "assistant", "content": response})

if __name__ == "__main__":
    chat_with_data()
