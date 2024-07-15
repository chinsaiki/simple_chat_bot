import streamlit as st
from chatbot import chatbot
import time
from PIL import Image
from chat_message import chat_message



class chatTab_conversation():
    def __init__(self, key='') -> None:
        self._key = key
        self._is_waiting = False
        self._with_assist = False

    def key(self, info):
        return f'{self._key}_{info}'


    def place_messages(self, bot:chatbot, infer_size:int):

        with st.container():
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
            if n==0 or message.role!='assistant':
                return st.empty()


    def place(self, bot:chatbot, is_dmy:bool, infer_size:int, assistant_icon:str):

        st.markdown(f"<a href='#linkto_btm_{self._key}'>跳到底部</a>", unsafe_allow_html=True)

        response_placeholder = self.place_messages(bot=bot, infer_size=infer_size)

        NEED_RERUN = False

        messages = bot.messages()
        if len(messages)==0:
            self._is_waiting = False
        else:
            last_request = messages[-1]
            self._is_waiting = last_request['role']=='user'

        # User-provided prompt
        if not self._is_waiting:
            cols = st.columns([11,1])
            with cols[1]:
                self._with_assist = st.checkbox('使用助手', value=False, disabled=not bot.assistant_ready(), key=self.key('with_assist'))
                st.markdown("<a href='#linkto_top'>回到顶部</a>", unsafe_allow_html=True)
            with cols[0]:
                if prompt := st.chat_input(key=self.key('chat_input')):
                    self._is_waiting = True
                    with st.chat_message("user"):
                        st.info(prompt)
                        try:
                            bot.on_user_input(prompt)
                            bot.save_profile_to_file()
                            NEED_RERUN = True
                        except Exception as e:
                            self._is_waiting = False
                            st.error(e)

        else:
            # st.chat_input(key=self.key('chat_input'), disabled=True)

            with st.chat_message("assistant", avatar=assistant_icon):
                with st.spinner(f"Thinking..."):
                    for retry in range(3):
                        try:
                            if is_dmy:
                                message = bot.dmy_response(5)
                            else:
                                if response_placeholder is None:
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

        st.markdown(f"<div id='linkto_btm_{self._key}'></div>", unsafe_allow_html=True)

        return NEED_RERUN

    