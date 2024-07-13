
import streamlit as st


class chatTab_properity():
    MSG_RANGE_MIN = 1
    MSG_RANGE_MAX = 9
    def __init__(self, key) -> None:
        self._key = key

        self._bot_dmy_chat = True
        self._bot_infer_size = 3
        self._bot_is_assistant = False
        self._bot_assistant_name = None
        self._bot_assistant_instruction = None
        self._bot_with_file = None
        self._bot_file_path = None

    def key(self, info):
        return f'{self._key}_{info}'

    def place_infer_size(self):
        with st.container(border=True):
            st.write("参考历史对话数")

            cols = st.columns([1,5,1])

            with cols[0]:
                st.write("\n")
                if st.button('➖', key=self.key('infer_size_dec')):
                    self.update_slider_state(-2)
            with cols[2]:
                st.write("\n")
                if st.button('➕', key=self.key('infer_size_inc')):
                    self.update_slider_state(2)
            with cols[1]:
                st.slider('chat range', min_value=chatTab_properity.MSG_RANGE_MIN, max_value=chatTab_properity.MSG_RANGE_MAX, 
                                        value=self._bot_infer_size, step=2, disabled=True, key=self.key('infer_size_slider'))

    def update_slider_state(self, delta):
        self._bot_infer_size += delta
        self._bot_infer_size = max(chatTab_properity.MSG_RANGE_MIN, min(chatTab_properity.MSG_RANGE_MAX, self._bot_infer_size))


    def place(self, on_chat_close):
        NEED_RERUN = False

        if st.button('关闭对话', key=self.key('btn_close')):
            on_chat_close(self._key)
            NEED_RERUN = True

        if st.button('重试', key=self.key('btn_retry')):
            NEED_RERUN = True

        self._bot_dmy_chat = st.checkbox('离线模式(测试用)', value=True, key=self.key('dmy_chat'))

        self.place_infer_size()

        return NEED_RERUN
