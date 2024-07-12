
import streamlit as st
from chatbot import chatbot
from chatbotAssist import chatbotAssist


class chatTab_properity():
    MSG_RANGE_MIN = 1
    MSG_RANGE_MAX = 9
    def __init__(self, profile=None) -> None:
        self._bot = chatbotAssist()
        self._bot.init(profile=profile)

        self._bot_dmy_chat = True
        self._bot_infer_size = 3
        self._bot_is_assistant = False
        self._bot_assistant_name = None
        self._bot_assistant_instruction = None
        self._bot_with_file = None
        self._bot_file_path = None

    def title(self):
        return self._bot.profile()['summary']

    def id(self):
        return self._bot.profile()['timestamp']

    def place_infer_size(self):
        NEED_RERUN = False
        col1, col2, col3 = st.columns([1,5,1])
        with col1:
            st.write("\n")
            if st.button('➖', key=f'{self.id()}_infer_size_dec'):
                self.update_slider_state(-2)
                NEED_RERUN = True
        with col2:
            st.slider('chat range', min_value=chatTab_properity.MSG_RANGE_MIN, max_value=chatTab_properity.MSG_RANGE_MAX, 
                                    value=self._bot_infer_size, step=2, disabled=True, key=f'{self.id()}_infer_size_slider')
        with col3:
            st.write("\n")
            if st.button('➕', key=f'{self.id()}_infer_size_inc'):
                self.update_slider_state(2)
                NEED_RERUN = True
        return NEED_RERUN

    def update_slider_state(self, delta):
        self._bot_infer_size += delta
        self._bot_infer_size = max(chatTab_properity.MSG_RANGE_MIN, min(chatTab_properity.MSG_RANGE_MAX, self._bot_infer_size))


    def place(self):
        NEED_RERUN = False
        if st.button('Retry', key=f'{self.id()}_btn_retry'):
            NEED_RERUN = True

        self._bot_dmy_chat = st.checkbox('Test local', value=self._bot_dmy_chat, key=f'{self.id()}_dmy_chat')

        NEED_RERUN |= self.place_infer_size()








        return NEED_RERUN
