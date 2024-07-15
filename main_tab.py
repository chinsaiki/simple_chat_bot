
import streamlit as st
from hisTab import hisTab
from chatTab import chatTab

st.set_page_config(page_title="🛸💬 Simple Chat Bot", layout="wide")

NEED_RERUN = False #

def on_new_chat():
    for ct in st.session_state.chatTabs:
        if ct.title()=='null':
            st.error('已有全新对话')
            return
    chat = chatTab()
    st.session_state.chatTabs.append(chat)
    global NEED_RERUN
    NEED_RERUN = True

def on_history_load(profile):
    chat = chatTab(profile=profile)
    for ct in st.session_state.chatTabs:
        if ct.id()==chat.id():
            st.error(f'无法重复加载')
            return
    st.session_state.chatTabs.append(chat)
    global NEED_RERUN
    NEED_RERUN = True

def on_history_delete(profile):
    on_chat_close(target_id=profile['timestamp'])

def on_chat_close(target_id):
    for i, item in enumerate(st.session_state.chatTabs):
        if item.id() == target_id:
            del st.session_state.chatTabs[i]
            break

    global NEED_RERUN
    NEED_RERUN = True


if 'chatTabs' not in st.session_state:
    st.session_state.chatTabs = []
if 'hisTab' not in st.session_state:
    st.session_state.hisTab = hisTab()

st.markdown("<div id='linkto_top'></div>", unsafe_allow_html=True)

tabNames = ['[对话列表]']
for ct in st.session_state.chatTabs:
    tabNames.append(f'[{ct.title(16)}]')
tabs = st.tabs(tabNames)

with tabs[0]:
    st.session_state.hisTab.place(on_new_chat=on_new_chat, on_load=on_history_load, on_delete=on_history_delete)

with st.sidebar:
    st.markdown("<a href='#linkto_top'>回到顶部</a>", unsafe_allow_html=True)
    for ct in st.session_state.chatTabs:
        st.markdown(f"《{ct.title()}》<a href='#linkto_btm_{ct.id()}'>跳到底部</a>", unsafe_allow_html=True)

index = 1
for ct in st.session_state.chatTabs:
    if index>=len(tabs): break
    with tabs[index]:
        NEED_RERUN |= ct.place(on_chat_close=on_chat_close)
    index += 1


if NEED_RERUN:
    st.rerun()
