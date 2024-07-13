
import streamlit as st
from chatbotAssist import chatbotAssist
from chatTab_conversation import chatTab_conversation
from chatTab_properity import chatTab_properity







class chatTab():
    def __init__(self, profile=None) -> None:
        self._bot = chatbotAssist()
        self._bot.init()
        if profile is not None:
            self._bot.load_profile_data(profile=profile)
        self._prop = chatTab_properity(key=self.id())
        self._conv = chatTab_conversation(key=self.id())

    def title(self, char_lmt=64):
        return self._bot.summary(char_lmt=char_lmt)

    def id(self):
        return self._bot.id()

    def place(self, on_chat_close):
        NEED_RERUN = False

        tabs = st.tabs(['对话', '控制'])

        with tabs[1]:
            NEED_RERUN |= self._prop.place(on_chat_close=on_chat_close)
        with tabs[0]:
            NEED_RERUN |= self._conv.place(
                bot=self._bot,
                is_dmy=self._prop._bot_dmy_chat,
                infer_size=self._prop._bot_infer_size,
                assistant_icon=None,
            )

        return NEED_RERUN