
import streamlit as st
from collections import OrderedDict

_NO_ASSIST_ = '不使用助手'

def list_assistants():
    ass = OrderedDict()
    ass['万能助手'] = ([], f'你是一个万能的AI智能助手，可以回答我的所有问题。')
    ass['万能助手-dash应用'] = ([], f'你是一个对python中dash模块非常熟悉的的AI智能助手，可以为我解释关于dash框架的原理，并提供代码示例。')
    ass['代码助手-数据可视化'] = ( [{"type": "code_interpreter"}],
                        f"You are a helpful AI assistant who makes interesting visualizations based on data.\n\n" \
                        f"You have access to a sandboxed environment for writing and testing code.\n\n" \
                        f"When you are asked to create a visualization you should follow these steps:\n\n" \
                        f"1. Write the code.\n\n" \
                        f"2. Anytime you write new code display a preview of the code to show your work.\n\n" \
                        f"3. Run the code to confirm that it runs.\n\n" \
                        f"4. If the code is successful display the visualization.\n\n" \
                        f"5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."
                        )
    ass['代码助手-dash应用'] = ( [{"type": "code_interpreter"}],
                        f"You are a helpful AI assistant who makes interesting web app based on dash module of python.\n\n" \
                        f"You have access to a sandboxed environment for writing and testing code.\n\n" \
                        f"When you are asked to create a app you should follow these steps:\n\n" \
                        f"1. Write the code.\n\n" \
                        f"2. Anytime you write new code display web view of the code to show your work.\n\n" \
                        f"3. Run the code to confirm that it runs.\n\n" \
                        f"4. If the code is successful interact with all web call.\n\n" \
                        f"5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."
                        )

    ass['文档助手'] = ( [{"type": "file_search"}],
                    f"你是一个可靠的文档智能助理，可以阅读多个文档信息并作出整理、总结和推理。\n\n" \
                    f"当我询问问题时，你按照以下步骤作出回应:\n\n" \
                    f"1. 从文档中查找相关信息，列出至少3个最接近问题的段落位置和摘要。\n\n" \
                    f"2. 总结相关信息并给出问题的答案。\n\n" \
                    f"3. 从文档之外你所知数据中提供问题答案的相关参考信息。"
                    )

    ass["specific document Analyst Assistant"] = ( [{"type": "file_search"}],
                        "You are a professional technical document analyst. Use your knowledge base to answer questions about specific document technologies."
                    )


    ass[_NO_ASSIST_] = ([], None)
    return ass

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

        self._assistant_list = list_assistants()

        self._timeout = 30

    def key(self, info):
        return f'{self._key}_{info}'

    def infer_size(self):
        if self._bot_infer_size>=chatTab_properity.MSG_RANGE_MAX:
            return 100
        return self._bot_infer_size


    def place_infer_size(self):
        with st.container(border=True):
            st.write("参考历史深度")

            cols = st.columns([1,5,1])

            with cols[0]:
                st.write("\n")
                if st.button('➖', key=self.key('infer_size_dec')):
                    self.update_slider_state(-2)
            with cols[2]:
                st.write("\n")
                if st.button('➕', key=self.key('infer_size_inc'), help=f'{chatTab_properity.MSG_RANGE_MAX}:无限(实际约100)'):
                    self.update_slider_state(2)
            with cols[1]:
                st.slider('chat range', min_value=chatTab_properity.MSG_RANGE_MIN, max_value=chatTab_properity.MSG_RANGE_MAX, 
                                        value=self._bot_infer_size, step=2, disabled=True, key=self.key('infer_size_slider'))

    def update_slider_state(self, delta):
        self._bot_infer_size += delta
        self._bot_infer_size = max(chatTab_properity.MSG_RANGE_MIN, min(chatTab_properity.MSG_RANGE_MAX, self._bot_infer_size))

    def place_delete_last_message(self, on_delete_last_message):
        NEED_RERUN = False
        with st.form(self.key('delete_last_msg'), True):
            cols = st.columns([2,1,4,2])
            with cols[1]:
                st.text('最后')
            with cols[2]:
                delete_nb = st.number_input('数量', value=0, min_value=0, step=1, format='%d', key=self.key('delete_msg_nb_input'), label_visibility='collapsed')
            with cols[3]:
                st.text('条消息')
            with cols[0]:
                submitted = st.form_submit_button("删除")
                if submitted and delete_nb>0:
                    # print(f'删除最后{delete_nb}条消息')
                    on_delete_last_message(delete_nb)
                    NEED_RERUN = True
        return NEED_RERUN

    def place_assistant(self, on_use_assist, on_reset_assist, on_qurey_assist):
        select_assist = st.selectbox('选择助手', list(self._assistant_list.keys()), index=len(list(self._assistant_list.keys()))-1, key=self.key('select_assist'))
        st.markdown(self._assistant_list[select_assist][1])
        with st.form(key=self.key('prop form'), border=False, clear_on_submit=False):
            use_code = st.checkbox('代码解释器', value=False, key=self.key('use_code'))
            file_search = st.checkbox('附加文档', value=False, key=self.key('use_file_search'))

            cols = st.columns(2)

            with cols[1]:
                qurey = st.form_submit_button('查询当前助手状态')
            with cols[0]:
                apply = st.form_submit_button('应用')
            if apply:
                if select_assist==_NO_ASSIST_:
                    on_reset_assist()
                else:
                    tools = self._assistant_list[select_assist][0]
                    if use_code:
                        already = False
                        for t,v in tools.items():
                            if t=='type' and v=='code_interpreter': already = True
                        if not already:
                            tools.append({"type": "code_interpreter"})
                    if file_search:
                        already = False
                        for t,v in tools.items():
                            if t=='type' and v=='file_search': already = True
                        if not already:
                            tools.append({"type": "file_search"})
                    with st.spinner('初始化...'):
                        on_use_assist(name=select_assist, instruction=self._assistant_list[select_assist][1], tools=tools)
            if apply or qurey:
                st.text(on_qurey_assist())    

    def place_assistant_files(self):
        pass
        # with st.form("upload-file", True):
        #     uploaded_file = st.file_uploader("上传文件", type=["pdf", "txt"], accept_multiple_files=False)
        #     submitted = st.form_submit_button("上传")
        #     if submitted and uploaded_file is not None:
        #         for retry in range(3):
        #             try:
        #                 st.session_state.chatbot.upload_file(uploaded_file.name, uploaded_file)
        #                 break
        #             except Exception as e:
        #                 st.error(f'{e}'[-20:])
        #                 st.error(f'#{retry} fail! Retrying...')
        #                 if retry==3-1: raise e
        #         st.success("上传成功")
        #         st.session_state.chatbot.with_file()
        #         # backup_file(st.session_state[DAMP_AP_CONFIG_SOURCE], st.success, st.error)

        #         # # 保存上传的文件
        #         # with open(st.session_state[DAMP_AP_CONFIG_SOURCE], "wb") as f:
        #         #     f.write(uploaded_file.getbuffer())
        #         # st.success(f'文件上传成功，保存到 {st.session_state[DAMP_AP_CONFIG_SOURCE]}')
        # st.session_state.with_file = st.checkbox('谈谈文件', value=False)

    def place_time_out(self):
        def on_change():
             self._timeout = st.session_state[self.key('timeout')]
        st.number_input(label='timeout', value=30, min_value=1, max_value=3600, step=1, key=self.key('timeout'), on_change=on_change)

    def place(self, on_chat_close, on_delete_last_message, on_use_assist, on_reset_assist, on_qurey_assist):
        NEED_RERUN = False

        col0, col1 = st.columns([4,4])
        with col0:

            self._bot_dmy_chat = st.checkbox('离线模式(测试用)', value=False, key=self.key('dmy_chat'))

            self.place_infer_size()

            self.place_time_out()

            NEED_RERUN |= self.place_delete_last_message(on_delete_last_message)

            btn_cols = st.columns([1,1])
            with btn_cols[0]:
                if st.button('关闭对话', key=self.key('btn_close')):
                    on_chat_close(self._key)
                    NEED_RERUN = True

            with btn_cols[1]:
                if st.button('重试', key=self.key('btn_retry')):
                    NEED_RERUN = True

        with col1:
            self.place_assistant(on_use_assist, on_reset_assist, on_qurey_assist)






        return NEED_RERUN
