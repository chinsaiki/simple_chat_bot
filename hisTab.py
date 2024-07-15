
import streamlit as st
from chatbot import chatbot


class hisTab():
    def __init__(self) -> None:
        self._profiles = {}
        self._deleted = []

    def list_profiles(self, refresh_keys, in_single_msg):
        self._profiles = chatbot.list_profiles(key_size=24, key_words=refresh_keys, in_single_msg=in_single_msg)

    def place(self, on_new_chat, on_load=None, on_delete=None):
        if st.button(f'新建对话'):
            on_new_chat()

        for index in self._deleted:
            self._profiles.pop(index)
        self._deleted = []

        with st.form('hisTab_refresh', clear_on_submit=False, border=False):
            refresh_cols = st.columns([0.1,0.4,0.2])
            with refresh_cols[1]:
                refresh_keys = st.text_input(label='过滤:关键字', value='', key='hisTab_keys')
            with refresh_cols[2]:
                st.text('')
                in_single_msg = st.checkbox(label='过滤:在单消息中查找', value=False, key='hisTab_in_single_msg')
            with refresh_cols[0]:
                st.text('')
                submitted = st.form_submit_button("刷新历史对话")
                if submitted:
                    self.list_profiles(refresh_keys, in_single_msg)

        with st.container(border=True, height=660):
            index = 0
            for summary, profile in self._profiles.items():
                msg_nb = len(profile['data']["messages"])

                with st.container(border=False):
                    cols = st.columns([3,6,1,1,1], vertical_alignment='top')
                    with cols[0]:
                        st.text(summary)
                    with cols[1]:
                        if msg_nb>1:
                            st.markdown(profile['data']["messages"][1]['content'][:80])
                        else:
                            st.write('[空]')
                    with cols[2]:
                        st.write(f'消息:{msg_nb}')
                    with cols[3]:
                        if st.button(f"加载", key=f'load-{index}'):
                            if on_load is not None:
                                on_load(profile['data'])
                    with cols[4]:
                        if st.button(f"删除", key=f'del-{index}'):
                            if on_delete is not None:
                                on_delete(profile['data'])
                            chatbot.delete_profile(profile['fname'])
                            self._deleted.append(summary)
                
                st.divider()
                index += 1



        return False