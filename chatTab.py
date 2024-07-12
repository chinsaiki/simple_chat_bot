
import streamlit as st
from chatTab_conversation import chatTab_conversation
from chatTab_properity import chatTab_properity







class chatTab():
    def __init__(self, profile=None) -> None:
        self._prop = chatTab_properity(profile=profile)
        self._conv = chatTab_conversation(key=self.id())

    def title(self):
        return self._prop.title()

    def id(self):
        return self._prop.id()

    def place(self):
        NEED_RERUN = False

        tabs = st.tabs(['对话', '属性'])

        with tabs[1]:
            NEED_RERUN |= self._prop.place()
        with tabs[0]:
            NEED_RERUN |= self._conv.place(
                bot=self._prop._bot,
                is_dmy=self._prop._bot_dmy_chat,
                infer_size=self._prop._bot_infer_size,
                assistant_icon=None,
            )

        return NEED_RERUN