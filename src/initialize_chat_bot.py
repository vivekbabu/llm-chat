import streamlit as st
from streamlit_chat import message
from large_language_model_utilities import chat_api


MAX_LENGTH_MODEL_DICT = {
    "gpt-4": 8191,
    "gpt-4o": 8192,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16384
}


def get_text():
    """Capture user input for data analysis"""
    input_text = st.chat_input(
        placeholder="Enter your data analysis request here...",
        key="user_input"
    )
    return input_text


def sidebar():
    """App sidebar content"""

    large_language_model = st.selectbox(
        label="Available Models",
        options=["gpt-3.5-turbo", "gpt-4", "gpt-3.5-turbo-16k"],
        help="""Choose a model to use. Note that the same prompt may yield different results
        across models. Experimentation is encouraged."""
    )

    temperature = st.slider(
        label="Temperature",
        value=0.05,
        min_value=0.,
        max_value=2.,
        step=0.01,
        help=(
            """Adjusts the randomness of the output. A value between 0 and 2, where higher values
            (e.g., 0.8) make the output more varied, while lower values (e.g., 0.2) make it more
            focused and predictable. It's advisable to modify either this or `top_p`, but not both."""
        )
    )
    maximum_tokens = st.slider(
        label="Maximum Length (Tokens)",
        value=4096,
        min_value=0,
        max_value=MAX_LENGTH_MODEL_DICT[large_language_model],
        step=1,
        help=(
            """Sets the maximum number of tokens for the generated output. Keep in mind that the
            total number of input and output tokens is constrained by the model's context length."""
        )
    )
    top_p = st.slider(
        label="Top P",
        value=0.5,
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        help=(
            """Controls the diversity of the output through nucleus sampling. The model will
            consider tokens within the top `top_p` probability mass. For example, a value of 0.1
            limits the output to the top 10% most likely tokens. It's recommended to adjust either
            this or `temperature`, but not both."""
        )
    )
    output_dictionary = {
        "model": large_language_model,
        "temperature": temperature,
        "max_tokens": maximum_tokens,
        "top_p": top_p,
    }
    return output_dictionary


def chatbot():
    """
    Main chatbox function based on ChatCompletion API
    """

    st.title("Chat with and Plot the data")

    with st.sidebar:
        model_params = sidebar()

    greeting_bot_msg = (
        "Hi, I am not a just a chatbot. I can plot fetched data for you. "
        "Ask me questions like 'What was US, UK and Germany's GDP in 2019 and 2020?'. "
        "Once the data is received, ask me to plot it."
    )

    # Storing the chat
    if "generated" not in st.session_state:
        st.session_state["generated"] = [greeting_bot_msg]

    if "past" not in st.session_state:
        st.session_state["past"] = []

    prompt = "You are a chatbot that answers questions. You can also plot data if asked"
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "system", "content": prompt}]

    user_input = get_text()

    if ((len(st.session_state["past"]) > 0)
            and (user_input == st.session_state["past"][-1])):
        user_input = ""

    if user_input:
        st.session_state["messages"].append(
            {"role": "user", "content": user_input}
        )
        response = chat_api(st.session_state["messages"], **model_params)
        st.session_state.past.append(user_input)
        if response is not None:
            st.session_state.generated.append(response)
            st.session_state["messages"].append({
                "role": "assistant",
                "content": response
            })

    if st.session_state["generated"]:
        for i in range(len(st.session_state["generated"]) - 1, -1, -1):
            message(st.session_state["generated"][i], key=str(i))
            if i - 1 >= 0:
                message(
                    st.session_state["past"][i - 1],
                    is_user=True,
                    key=str(i) + "_user"
                )


if __name__ == "__main__":
    chatbot()
