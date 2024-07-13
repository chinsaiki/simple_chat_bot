
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

    def place_delete_last_message(self, on_delete_last_message):
        NEED_RERUN = False
        with st.form("upload-file", True):
            cols = st.columns([2,1,4,2])
            with cols[1]:
                st.text('最后')
            with cols[2]:
                delete_nb = st.number_input('数量', value=0, min_value=0, step=1, format='%d', key=self.key('delete_msg_nb_input'), label_visibility='collapsed')
            with cols[3]:
                st.text('条消息')
            with cols[0]:
                submitted = st.form_submit_button("删除")
                if submitted:
                    # print(f'删除最后{delete_nb}条消息')
                    on_delete_last_message(delete_nb)
                    NEED_RERUN = True
        return NEED_RERUN

    def place(self, on_chat_close, on_delete_last_message):
        NEED_RERUN = False

        col0, _ = st.columns([2,4])
        with col0:
            if st.button('关闭对话', key=self.key('btn_close')):
                on_chat_close(self._key)
                NEED_RERUN = True

            if st.button('重试', key=self.key('btn_retry')):
                NEED_RERUN = True

            self._bot_dmy_chat = st.checkbox('离线模式(测试用)', value=True, key=self.key('dmy_chat'))

            self.place_infer_size()

            NEED_RERUN |= self.place_delete_last_message(on_delete_last_message)

        return NEED_RERUN
