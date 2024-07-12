
import streamlit as st
from hisTab import hisTab
from chatTab import chatTab

st.set_page_config(page_title="🛸💬 Simple Chat Bot", layout="wide")

NEED_RERUN = False #


def on_history_load(profile):
    st.session_state.chatTabs.append(chatTab(profile=profile))
    global NEED_RERUN
    NEED_RERUN = True

def on_history_delete(profile):
    target_id = profile['timestamp']
    for i, item in enumerate(st.session_state.chatTabs):
        if id(item) == target_id:
            del st.session_state.chatTabs[i]
            print(f"Element with id {target_id} removed.")
            # global NEED_RERUN
            NEED_RERUN = True
            return

if 'chatTabs' not in st.session_state:
    st.session_state.chatTabs = []
if 'hisTab' not in st.session_state:
    st.session_state.hisTab = hisTab()

tabNames = ['history']
for ct in st.session_state.chatTabs:
    tabNames.append(ct.title())
tabs = st.tabs(tabNames)

with tabs[0]:
    st.session_state.hisTab.place(on_load=on_history_load, on_delete=on_history_delete)

index = 1
for ct in st.session_state.chatTabs:
    if index>=len(tabs): break
    with tabs[index]:
        NEED_RERUN |= ct.place()
    index += 1

if NEED_RERUN:
    st.rerun()
