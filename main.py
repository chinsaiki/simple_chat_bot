import streamlit as st
import streamlit.config as stopt
from chatbot import chatbot
import pyperclip
import time
import os
import signal

NEED_RERUN = False #
EMPTY_PROFILE = '[ClickToChose]'
MSG_RANGE_MIN = 1
MSG_RANGE_MAX = 9

def get_current_port():
    return stopt.get_option('server.port')

def update_slider_state(delta):
    st.session_state.message_range += delta
    st.session_state.message_range = max(MSG_RANGE_MIN, min(MSG_RANGE_MAX, st.session_state.message_range))

    global NEED_RERUN
    NEED_RERUN = True



def new_chat(profile=None):
    if profile is None:
        profile = None if st.session_state.new_chat else st.session_state.current_profile
        if st.session_state.new_chat:
            st.success(f'New chat!')
            st.session_state.current_topic = None
            st.session_state.profiles = {}
        else:
            st.success(f'Refreshed.')
    else:
        st.success('Load chat {}'.format(profile['summary'][:64]))
    st.session_state.chatbot.init(
                                    profile = profile
                                )
    global NEED_RERUN
    NEED_RERUN = True


st.set_page_config(page_title="🤗💬 Simple Chat Bot")

if 'chatbot' not in st.session_state.keys():
    st.session_state.chatbot = chatbot()
if 'is_waiting' not in st.session_state:
    st.session_state.is_waiting = False
if 'is_dmy' not in st.session_state:
    st.session_state.is_dmy = False
# if 'is_stream' not in st.session_state:
    # st.session_state.is_stream = True
if 'message_range' not in st.session_state:
    st.session_state.message_range = 3
if 'new_chat' not in st.session_state:
    st.session_state.new_chat = True
if 'current_profile' not in st.session_state:
    st.session_state.current_profile = None
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = None
if 'profiles' not in st.session_state:
    st.session_state.profiles = {}

with st.sidebar:
    port = get_current_port()
    if port is not None:
        st.write(f"💬 Simple Chat Bot (Port:{port})") 
    else:
        st.error("Failed to retrieve the current port.")

    col1, col2, _ = st.columns(3)
    with col1:
        if st.button('Exit', key='EXIT'):
            os.kill(os.getpid(), signal.SIGINT)
    with col2:
        if st.button('Retry', key='RETRY'):
            NEED_RERUN = True

    st.session_state.is_dmy = st.checkbox('Test local', value=False)
    # st.session_state.is_stream = st.checkbox('stream', value=True)
    

    col1, col2, col3 = st.columns([1,5,1])
    with col1:
        st.write("\n")
        if st.button('➖'):
            update_slider_state(-2)
    with col2:
        st.slider('chat range', min_value=MSG_RANGE_MIN, max_value=MSG_RANGE_MAX, value=st.session_state.message_range, step=2, disabled=True)
    with col3:
        st.write("\n")
        if st.button('➕'):
            update_slider_state(2)


    col1, col2 = st.columns([1,2])
    with col1:
        if st.button('Restart', key='RESTART', disabled=st.session_state.is_waiting):
            new_chat()
    with col2:
        st.session_state.new_chat = st.checkbox('new chat', value=True)

    if st.button('List Topics'):
        st.session_state.profiles = chatbot.list_profiles()
        st.session_state.profiles[EMPTY_PROFILE] = {}

    selected_topic = st.selectbox('Select a chat', list(st.session_state.profiles.keys()), index=len(st.session_state.profiles)-1, label_visibility='collapsed')
    if selected_topic and EMPTY_PROFILE!=selected_topic and selected_topic!=st.session_state.current_topic:
        st.session_state.current_topic = selected_topic
        new_chat(st.session_state.profiles[selected_topic]['data'])

# Display chat messages
n = len(st.session_state.chatbot.messages())
for message in st.session_state.chatbot.messages():
    inside_msg = n <= st.session_state.message_range  - (not st.session_state.is_waiting)
    if message["role"] == "user":
        with st.chat_message(message["role"]):
            text = message["content"]
            col1, col2 = st.columns([12,1])
            with col1:
                st.markdown("```\n{}\n```".format(text))
            with col2:
                #pyperclip.copy fail on Linux, do not use this button any more.
                # if st.button('Copy', key=f'conversation_{n}', on_click=lambda:pyperclip.copy(text), disabled=st.session_state.is_waiting):
                #     st.success(f'Copied!')
                if inside_msg:
                    st.write('💬')
    else:
        with st.chat_message(message["role"]):
            response = message["content"]
            col1, col2 = st.columns([12,1])
            with col1:
                st.markdown(response)
            with col2:
                #pyperclip.copy fail on Linux, do not use this button any more.
                # if st.button('Copy', key=f'conversation_{n}', on_click=lambda:pyperclip.copy(response), disabled=st.session_state.is_waiting):
                #     st.success(f'Copied!')
                if inside_msg:
                    st.write('💬')
    n -= 1

st.markdown( #just for PC, we expand the conversation area
    """
    <style>
        .stChatMessage {
            width: 160%;
            margin-left: -210px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown( #just for PC, we expand the conversation area
    """
    <style>
        .stChatFloatingInputContainer {
            background-color: transparent !important;
            bottom:-7%
        }
        /* Additional custom styles */
    </style>
    """,
    unsafe_allow_html=True,
)
 
def update_stream(placeholder, infer_size):
    response = st.session_state.chatbot.generate_event(infer_size=infer_size) 
    collected_messages = []

    for chunk in response:
        if len(chunk.choices):
            chunk_message = chunk.choices[0].delta.content
            if chunk_message is not None:
                collected_messages.append(chunk_message)
                message = ''.join(collected_messages)
                placeholder.markdown(message)
            else:
                return message
        time.sleep(0.03)

# User-provided prompt
if not st.session_state.is_waiting:
    if prompt := st.chat_input():
        st.session_state.is_waiting = True
        with st.chat_message("user"):
            st.session_state.chatbot.on_user_input(prompt)
            st.session_state.current_profile = st.session_state.chatbot.profile()
            st.session_state.chatbot.save_profile()
            NEED_RERUN = True
else:
    st.chat_input(disabled=True)
    infer_size = st.session_state.message_range
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            for retry in range(3):
                try:
                    if st.session_state.is_dmy:
                        message = st.session_state.chatbot.dmy_response(1)
                    else:# st.session_state.is_stream:
                        response_placeholder = st.empty()
                        message = update_stream(response_placeholder, infer_size=infer_size)
                    # else:
                    #     message = st.session_state.chatbot.generate_response(infer_size=infer_size)
                    break
                except Exception as e:
                    st.error(f'#{retry} fail! Retrying...')
                    if retry==3-1: raise e
                    time.sleep(1)

            st.session_state.chatbot.on_ai_response(message)
            st.session_state.current_profile = st.session_state.chatbot.profile()
            st.session_state.chatbot.save_profile()
            NEED_RERUN = True

            st.session_state.is_waiting = False

if NEED_RERUN:
    st.rerun()