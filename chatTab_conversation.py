import streamlit as st
from chatbot import chatbot
import time
from PIL import Image
from chat_message import chat_message


 
def get_bot_message(bot:chatbot, placeholder, infer_size:int):
    message = ''
    response = bot.generate_event(infer_size=infer_size) 
    if response is None: #不支持事件
        return bot.generate_response(infer_size=infer_size)
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


class chatTab_conversation():
    def __init__(self, key='') -> None:
        self._is_waiting = False
        self._key = key


    def place_messages(self, bot:chatbot, infer_size:int):

        with st.container(height=550):
            # st.markdown( #just for PC, we expand the conversation area
            #     """
            #     <style>
            #         .stChatMessage {
            #             width: 160%;
            #             margin-left: -210px;
            #         }
            #     </style>
            #     """,
            #     unsafe_allow_html=True,
            # )
            

            # Display chat messages
            messages = bot.messages()
            n = len(messages)
            for message_map in messages:
                inside_msg = n <= (infer_size  - (not self._is_waiting))

                message = chat_message.load(message_map)

                if message.role == "user":
                    with st.chat_message(message.role):
                        col1, col2 = st.columns([12,1])
                        with col1:
                            st.markdown("```\n{}\n```".format(message.content))
                        with col2:
                            if inside_msg:
                                st.write('💬')
                else:
                    with st.chat_message(message.role, avatar=message.assistant_icon):
                        col1, col2 = st.columns([12,1])
                        with col1:
                            if message.content_type=='image_file':
                                image = Image.open(message.content)
                                st.image(image)
                            else:
                                st.markdown(message.content)
                        with col2:
                            if inside_msg:
                                st.write('💬')
                n -= 1

    def place_chat_message(self, bot:chatbot):
        # CSS 样式，用于定义滚动框的样式
        st.markdown(
            """
            <style>
            .chat-box {
                max-height: 300px;
                overflow-y: auto;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            .chat-message {
                padding: 5px;
                margin-bottom: 5px;
                border-bottom: 1px solid #ddd;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        messages = bot.messages()
        st.markdown('<div class="chat-box">', unsafe_allow_html=True)

        for message_map in messages:
            message = chat_message.load(message_map)
            st.markdown(f'<div class="chat-message">{message.content}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)




    def place(self, bot:chatbot, is_dmy:bool, infer_size:int, assistant_icon:str):
        self.place_messages(bot=bot, infer_size=infer_size)
        # self.place_chat_message(bot)

        NEED_RERUN = False


        # st.markdown( #just for PC, we expand the conversation area
        #     """
        #     <style>
        #         .stChatFloatingInputContainer {
        #             background-color: transparent !important;
        #             bottom:-7%
        #         }
        #         /* Additional custom styles */
        #     </style>
        #     """,
        #     unsafe_allow_html=True,
        # )

        # User-provided prompt
        if not self._is_waiting:
            if prompt := st.chat_input():
                self._is_waiting = True
                with st.chat_message("user"):
                    st.info(prompt)
                    try:
                        bot.on_user_input(prompt)
                        bot.save_profile()
                        NEED_RERUN = True
                    except:
                        self._is_waiting = False

            # with st.form(f"{self._key}_User input form", True):
            #     cols = st.columns([6,1])
            #     with cols[0]:
            #         prompt = st.text_input("User input", value='', key=f"{self._key}_user_input", label_visibility='collapsed')
            #     with cols[1]:
            #         submitted = st.form_submit_button("▶️")
            #     if submitted and len(prompt):
            #         self._is_waiting = True
            #         with st.chat_message("user"):
            #             st.info(prompt)
            #             try:
            #                 bot.on_user_input(prompt)
            #                 bot.save_profile()
            #                 NEED_RERUN = True
            #             except:
            #                 self._is_waiting = False

        else:
            st.chat_input(disabled=True)

            # with st.form(f"{self._key}_User input form", True):
            #     cols = st.columns([6,1])
            #     with cols[0]:
            #         prompt = st.text_input("User input", value='', key=f"{self._key}_user_input", label_visibility='collapsed', disabled=True)
            #     with cols[1]:
            #         submitted = st.form_submit_button("▶️", disabled=True)


            with st.chat_message("assistant", avatar=assistant_icon):
                with st.spinner("Thinking..."):
                    for retry in range(3):
                        try:
                            if is_dmy:
                                message = bot.dmy_response(1)
                            else:
                                response_placeholder = st.empty()
                                message = get_bot_message(bot, response_placeholder, infer_size=infer_size)
                            break
                        except Exception as e:
                            st.error(f'{e}'[:40])
                            st.error(f'#{retry} fail! Retrying...')
                            if retry==3-1: raise e
                            time.sleep(1)

                    bot.on_ai_response(message)
                    bot.save_profile()
                    NEED_RERUN = True

                    self._is_waiting = False

        return NEED_RERUN

    