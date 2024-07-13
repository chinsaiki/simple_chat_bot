import streamlit as st
from chatbot import chatbot
import time
from PIL import Image
from chat_message import chat_message



class chatTab_conversation():
    def __init__(self, key='') -> None:
        self._key = key
        self._is_waiting = False

    def key(self, info):
        return f'{self._key}_{info}'


    def place_messages(self, bot:chatbot, infer_size:int):

        with st.container(height=550):
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


    def place(self, bot:chatbot, is_dmy:bool, infer_size:int, assistant_icon:str):
        self.place_messages(bot=bot, infer_size=infer_size)

        NEED_RERUN = False

        messages = bot.messages()
        if len(messages)==0:
            self._is_waiting = False
        else:
            last_request = messages[-1]
            self._is_waiting = last_request['role']=='user'

        # User-provided prompt
        if not self._is_waiting:
            if prompt := st.chat_input(key=self.key('chat_input')):
                self._is_waiting = True
                with st.chat_message("user"):
                    st.info(prompt)
                    try:
                        bot.on_user_input(prompt)
                        bot.save_profile_to_file()
                        NEED_RERUN = True
                    except:
                        self._is_waiting = False

        else:
            # st.chat_input(key=self.key('chat_input'), disabled=True)

            with st.chat_message("assistant", avatar=assistant_icon):
                with st.spinner(f"Thinking..."):
                    for retry in range(3):
                        try:
                            if is_dmy:
                                message = bot.dmy_response(5)
                            else:
                                response_placeholder = st.empty()
                                message = bot.generate_stream_response(response_placeholder, infer_size=infer_size)
                            break
                        except Exception as e:
                            if retry==0:
                                st.info('>' + last_request['content'])
                            st.error(f'#{retry} 失败:{e}  准备重试...')
                            if retry==3-1: raise e
                            time.sleep(1)

                    bot.on_ai_response(message)
                    bot.save_profile_to_file()
                    NEED_RERUN = True

                    self._is_waiting = False

        return NEED_RERUN

    