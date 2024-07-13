
import streamlit as st
from chatbot import chatbot


class hisTab():
    def __init__(self) -> None:
        self._profiles = {}
        self._deleted = []

    def list_profiles(self):
        self._profiles = chatbot.list_profiles(key_size=32)

    def place(self, on_new_chat, on_load=None, on_delete=None):
        if st.button(f'新建对话'):
            on_new_chat()

        for index in self._deleted:
            self._profiles.pop(index)
        self._deleted = []


        if st.button(f'刷新历史对话'):
            self.list_profiles()

        index = 0
        for summary, profile in self._profiles.items():
            msg_nb = len(profile['data']["messages"])

            with st.container(border=False):
                cols = st.columns([2,4,1,1,1])
                with cols[0]:
                    st.write(summary)
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
            index += 1


        return False