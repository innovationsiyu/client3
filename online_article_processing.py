import streamlit as st
import validators
import json
import ast
import requests
import os
from scraper import get_web_text
from yusi_tools import internal_text_chat, filter_words
from yusi_utils import upload_to_container


def load_user_info():
    url = "https://yusistorage.blob.core.windows.net/user-config/Yijie.txt"
    try:
        response = requests.get(url)
        user_info = eval(response.text)
        return user_info
    except Exception as e:
        st.warning(f"Error in load_user_info: {e}. Please check the network.")
        return {"prompts_for_processing": [], "words_for_filtering": []}


def save_user_info():
    txt_path = "Yijie.txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(str(st.session_state["user_info"]))
        upload_to_container(txt_path)
        os.remove(txt_path)
    except Exception as e:
        st.warning(f"Error in save_user_info: {e}. Please check the network.")


def update_user_info():
    st.session_state["user_info"] = {
        "prompts_for_processing": st.session_state["user_info"].get("prompts_for_processing", []),
        "words_for_filtering": st.session_state["user_info"].get("words_for_filtering", [])
    }
    save_user_info()


def is_valid_string_list(input_str):
    try:
        parsed = ast.literal_eval(input_str)
        return isinstance(parsed, list) and all(isinstance(item, str) for item in parsed)
    except Exception:
        return False


def is_valid_url(url):
    return validators.url(url)


def append_user_message(content):
    st.session_state["chat_history"].append({"role": "user", "content": content})


def append_assistant_message(content):
    st.session_state["chat_history"].append({"role": "assistant", "content": content})


st.session_state["chat_history"] = st.session_state.get("chat_history", [{"role": "assistant", "content": "可以通过左侧的多个按钮选择、编辑、添加对文章的处理要求和从大模型的输出中过滤掉的字符"}])
st.session_state["user_info"] = st.session_state.get("user_info", load_user_info())
prompts_for_processing = st.session_state["user_info"].get("prompts_for_processing", [])
st.session_state["selected_prompt"] = st.session_state.get("selected_prompt", prompts_for_processing[0]["prompt"] if prompts_for_processing else "")
words_for_filtering = st.session_state["user_info"].get("words_for_filtering", [])


def process_article(target_url):
    selected_prompt = st.session_state["selected_prompt"]
    if selected_prompt:
        system_message = next(prompt["prompt_value"] for prompt in st.session_state["user_info"]["prompts_for_processing"] if prompt["prompt"] == selected_prompt)
        user_message = f"<article>{get_web_text(target_url)}</article>"
        results = internal_text_chat("GPT for article processing", system_message, user_message)
        if results:
            results = filter_words(results, st.session_state["user_info"].get("words_for_filtering", []))
            return results
    return None


st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Article Processing for Yijie</h1>", unsafe_allow_html=True)
user_info_column, interaction_column = st.columns([1, 3])

with interaction_column:
    with st.container(height=520, border=True):
        for message in st.session_state["chat_history"]:
            role = message["role"]
            content = message["content"]
            if role == "user":
                with st.chat_message("user"):
                    st.write(f"User:\n{content}")
            else:
                with st.chat_message("assistant"):
                    st.write(f"AI:\n{content}")

    user_message = st.chat_input("在这里粘贴文章的URL，仅输入URL")

    if user_message and is_valid_url(user_message):
        append_user_message(user_message)

        with st.spinner("Summarising the article..."):
            assistant_message = process_article(user_message)
            if assistant_message:
                append_assistant_message(assistant_message)
                st.rerun()


@st.dialog("Add a prompt for processing", width="small")
def add_prompt_for_processing_dialog():
    with st.form(key="add_prompt_for_processing_form"):
        prompt = st.text_input(label="Name the prompt").strip()
        prompt_value = st.text_area(label="Input a prompt").strip()
        if st.form_submit_button("Submit"):
            if prompt and prompt_value:
                st.session_state["user_info"]["prompts_for_processing"].append({"prompt": prompt, "prompt_value": prompt_value})
                update_user_info()
                st.success("Added successfully.")
                st.rerun()
            else:
                st.warning("Valid input required.")


@st.dialog("Add a word for filtering", width="small")
def add_word_for_filtering_dialog():
    with st.form(key="add_word_for_filtering_form"):
        word_for_filtering = st.text_input(label="Input a word").strip()
        if st.form_submit_button("Submit"):
            if word_for_filtering:
                st.session_state["user_info"]["words_for_filtering"].append(word_for_filtering)
                update_user_info()
                st.success("Added successfully.")
                st.rerun()
            else:
                st.warning("Valid input required.")


with user_info_column:
    if prompts_for_processing:
        prompts = [prompt["prompt"] for prompt in prompts_for_processing]
        selected_pill = st.pills("Choose how to process the article.", prompts, key="selected_prompt")
    else:
        st.session_state["selected_prompt"] = ""

    for prompt in prompts_for_processing:
        with st.expander(prompt["prompt"]):
            with st.form(key=f"update_prompt_for_processing_form_{prompt['prompt']}"):
                prompt_value_input = st.text_area(value=prompt["prompt_value"], height=200, label="Prompt for processing", label_visibility="collapsed")
                if st.form_submit_button("Submit"):
                    if prompt_value_input.strip():
                        prompt["prompt_value"] = prompt_value_input
                        update_user_info()
                        st.success("Updated successfully.")
                    else:
                        prompts_for_processing.remove(prompt)
                        update_user_info()
                        st.success("Deleted successfully.")

    if words_for_filtering:
        with st.expander("Words for Filtering"):
            with st.form(key="update_words_for_filtering_form"):
                words_for_filtering_input = json.dumps(words_for_filtering, ensure_ascii=False)
                words_for_filtering_input = st.text_area(value=words_for_filtering_input, height=200, label="Words for Filtering", label_visibility="collapsed")
                if st.form_submit_button("Submit"):
                    if words_for_filtering_input.strip():
                        if is_valid_string_list(words_for_filtering_input):
                            st.session_state["user_info"]["words_for_filtering"] = ast.literal_eval(
                                words_for_filtering_input)
                            update_user_info()
                            st.success("Updated successfully.")
                        else:
                            st.warning("Valid input required.")
                    else:
                        st.session_state["user_info"]["words_for_filtering"] = []
                        update_user_info()
                        st.success("Deleted successfully.")

    if st.button("Add a prompt for processing", key="add_prompt_button"):
        add_prompt_for_processing_dialog()

    if st.button("Add a word for filtering", key="add_word_button"):
        add_word_for_filtering_dialog()
