import streamlit as st
import streamlit.config as stopt
from chatbot import chatbot
from chatbotAssist import chatbotAssist
import pyperclip
import time
import os
import signal
from PIL import Image

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

def list_assistants():
    ass ={}
    ass.update()
    ass['代码助手-数据可视化'] = f"You are a helpful AI assistant who makes interesting visualizations based on data." \
                        f"You have access to a sandboxed environment for writing and testing code." \
                        f"When you are asked to create a visualization you should follow these steps:" \
                        f"1. Write the code." \
                        f"2. Anytime you write new code display a preview of the code to show your work." \
                        f"3. Run the code to confirm that it runs." \
                        f"4. If the code is successful display the visualization." \
                        f"5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."

    ass['文档助手'] = f"你是一个可靠的文档智能助理，可以阅读多个文档信息并作出整理、总结和推理。" \
                      f"当我询问问题时，你按照以下步骤作出回应:" \
                      f"1. 从文档中查找相关信息，列出至少3个最接近问题的段落位置和摘要。" \
                      f"2. 总结相关信息并给出问题的答案。" \
                      f"3. 从文档之外你所知数据中提供问题答案的相关参考信息。"

    ass["specific document Analyst Assistant"] = "You are an expert specific document analyst. Use your knowledge base to answer questions about audited specific document statements."

    return ass


def new_chat(profile=None):
    if profile is None:
        profile = None if st.session_state.new_chat else st.session_state.current_profile
        if st.session_state.new_chat:
            st.success(f'New chat!')
            st.session_state.current_topic = None
            st.session_state.profiles = {}
            st.session_state.current_assistant = None
            st.session_state.assistants = {}
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
    st.session_state.chatbot = chatbotAssist()
if 'is_waiting' not in st.session_state:
    st.session_state.is_waiting = False
if 'is_dmy' not in st.session_state:
    st.session_state.is_dmy = False
# if 'is_stream' not in st.session_state:
    # st.session_state.is_stream = True
if 'is_assistant' not in st.session_state:
    st.session_state.is_assistant = False
if 'with_file' not in st.session_state:
    st.session_state.with_file = False
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

if 'current_assistant' not in st.session_state:
    st.session_state.current_assistant = None
if 'assistants' not in st.session_state:
    st.session_state.assistants = {}

if 'current_vector_store' not in st.session_state:
    st.session_state.current_vector_store = None
if 'vector_stores' not in st.session_state:
    st.session_state.vector_stores = {}

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


    if st.button('列出助手'):
        st.session_state.assistants = list_assistants()
        st.session_state.assistants[EMPTY_PROFILE] = ""

    selected_assistant = st.selectbox('选择助手', list(st.session_state.assistants.keys()), index=len(st.session_state.assistants)-1, label_visibility='collapsed')
    if selected_assistant and EMPTY_PROFILE!=selected_assistant and (selected_assistant!=st.session_state.current_assistant or not st.session_state.chatbot.assistant_ready()):
        with st.spinner("Initializing..."):
            st.session_state.current_assistant = selected_assistant
            for retry in range(3):
                try:
                    st.session_state.chatbot.init_assistant(selected_assistant, st.session_state.assistants[selected_assistant])
                    break
                except Exception as e:
                    st.error(f'{e}'[-20:])
                    st.error(f'#{retry} fail! Retrying...')
                    if retry==3-1: raise e
            st.success("助手已初始化")
    st.session_state.is_assistant = st.checkbox('助手模式', value=False)


    if st.button('列出文档库'):
        #st.session_state.vector_stores = 
        st.session_state.chatbot.list_vector_stores()
        #st.session_state.vector_stores[EMPTY_PROFILE] = ""

    # selected_assistant = st.selectbox('选择助手', list(st.session_state.assistants.keys()), index=len(st.session_state.assistants)-1, label_visibility='collapsed')
    # if selected_assistant and EMPTY_PROFILE!=selected_assistant and selected_assistant!=st.session_state.current_assistant:
    #     with st.spinner("Initializing..."):
    #         st.session_state.current_assistant = selected_assistant
    #         st.session_state.chatbot.init_assistant(selected_assistant, st.session_state.assistants[selected_assistant])
    #         st.success("助手已初始化")
    # st.session_state.is_assistant = st.checkbox('助手模式', value=False)


    # 创建上传文件的组件
    with st.form("upload-file", True):
        uploaded_file = st.file_uploader("上传文件", type=["pdf", "txt"], accept_multiple_files=False)
        submitted = st.form_submit_button("上传")
        if submitted and uploaded_file is not None:
            for retry in range(3):
                try:
                    st.session_state.chatbot.upload_file(uploaded_file.name, uploaded_file)
                    break
                except Exception as e:
                    st.error(f'{e}'[-20:])
                    st.error(f'#{retry} fail! Retrying...')
                    if retry==3-1: raise e
            st.success("上传成功")
            st.session_state.chatbot.with_file()
            # backup_file(st.session_state[DAMP_AP_CONFIG_SOURCE], st.success, st.error)

            # # 保存上传的文件
            # with open(st.session_state[DAMP_AP_CONFIG_SOURCE], "wb") as f:
            #     f.write(uploaded_file.getbuffer())
            # st.success(f'文件上传成功，保存到 {st.session_state[DAMP_AP_CONFIG_SOURCE]}')
    st.session_state.with_file = st.checkbox('谈谈文件', value=False)





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
        response = message["content"]
        data_type = message["content_type"]
        assistant_name = '🤖' if 'assistant_name' in message and message['assistant_name'] is not None else None
        with st.chat_message(message["role"], avatar=assistant_name):
            col1, col2 = st.columns([12,1])
            with col1:
                if data_type=='image_file':
                    image = Image.open(response)
                    st.image(image)
                else:
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
    message = ''
    response = st.session_state.chatbot.generate_event(infer_size=infer_size) 
    if response is None: #不支持事件
        return st.session_state.chatbot.generate_response(infer_size=infer_size)
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
            st.info(prompt)
            try:
                st.session_state.chatbot.on_user_input(prompt, with_file=st.session_state.with_file)
                st.session_state.current_profile = st.session_state.chatbot.profile()
                st.session_state.chatbot.save_profile()
                NEED_RERUN = True
            except:
                st.session_state.is_waiting = False
else:
    st.chat_input(disabled=True)
    infer_size = st.session_state.message_range
    assistant_name = '🤖' if st.session_state.is_assistant and st.session_state.chatbot.assistant_ready() else None
    with st.chat_message("assistant", avatar=assistant_name):
        with st.spinner("Thinking..."):
            for retry in range(3):
                try:
                    if st.session_state.is_dmy:
                        message = st.session_state.chatbot.dmy_response(1)
                    elif assistant_name is not None:
                        message = st.session_state.chatbot.generate_response(infer_size=infer_size)
                    else:
                        response_placeholder = st.empty()
                        message = update_stream(response_placeholder, infer_size=infer_size)
                    break
                except Exception as e:
                    st.error(f'{e}'[:40])
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