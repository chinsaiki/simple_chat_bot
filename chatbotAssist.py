import os
import json
import datetime
import time
from weakref import ref
from openai.pagination import SyncCursorPage
from openai.types.beta import Thread
from openai.types.beta.threads import Message
from openai import AzureOpenAI
from typing import List

from chatbot import chatbot

ASSIST_NAME = 'assist_name'
ASSIST_INST = 'assist_instruction'


def parse_thread_messages(client:AzureOpenAI, thread:Thread, assistant_name:str):
    thread_messages = client.beta.threads.messages.list(
                                                        thread_id =thread.id
                                                    )
    message_infos = []
    for message in thread_messages.data[::-1]: #data[0]是最新的消息
        message_infos.extend(parse_thread_message(message, client, thread, assistant_name))

    return message_infos

def parse_thread_message(thread_message:Message, client:AzureOpenAI, thread:Thread, assistant_name:str ):
    message_infos = []
    for content in thread_message.content:
        if content.type=='text':

            message_content = content.text
            annotations = message_content.annotations
            citations = []
            for index, annotation in enumerate(annotations):
                message_content.value = message_content.value.replace(
                    annotation.text, f"[{index}]"
                )
                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = client.files.retrieve(file_citation.file_id)
                    citations.append(f"[{index}] {cited_file.filename}")

            text = message_content.value.strip() + "\n" + '\n'.join(citations)
            message_info = {
                            "role": thread_message.role,
                            "content":text,
                            "content_type":'text',
                        }

        elif content.type=='image_file':
            image_file_id = content.image_file.file_id
            content = client.files.content(image_file_id)
            if not os.path.exists(chatbotAssist.IMAGE_DIR):
                os.mkdir(chatbotAssist.IMAGE_DIR)
            save_path = os.path.join(chatbotAssist.IMAGE_DIR, f'{image_file_id}.png')
            image = content.write_to_file(save_path)
            message_info = {
                            "role": thread_message.role,
                            "content":save_path,
                            "content_type":'image_file',
                            }
        else:
            raise Exception(f'Not support content.type={content.type}')

        if thread_message.role=='assistant':
            message_info['assistant_name'] = assistant_name
            message_info['tool_resources'] = thread.tool_resources.model_dump_json(indent=2)
        message_infos.append(message_info)

    return message_infos


def search_thread_msg(messages, thread_messages):
    th_msg = thread_messages[-1]
    size = len(thread_messages)
    smax = len(messages)
    # print(f'search_thread_msg {smax} vs. {size}')
    for i, msg in enumerate(messages[::-1]):
        # print(f"  #-{i} {msg['content']}")
        if smax-i<size: #不足
            return True, 0
        if msg['role']==th_msg['role'] and msg['content']==th_msg['content']:
            # print(f'    match th, [{-size-i}:{-1-i}]')
            unmath = False
            for a, b in zip(messages[-size-i:-1-i], thread_messages[:-1]):
                # print(f"      A={a['role'] + ':' + a['content']} B={b['role'] + ':' + b['content']}")
                if a['role']!=b['role'] or a['content']!=b['content']:
                    # print('                    ^^ unmatch')
                    unmath = True
                    break
            if not unmath:
                return False, -1-i
        # else:
        #     print('  unmatch th')

    return True, 0


class dmy_ass():
    name: str
    id: str
    instruction: str
    tools:str

    def model_dump_json(self, indent):
        return json.dumps({
                            'name':self.name,
                            'id':self.id,
                            'instruction':self.instruction,
                            'tools':self.tools,
                            }, 
                            indent=indent)

class chatbotAssist(chatbot):
    IMAGE_DIR = os.path.join(chatbot.HISTORY_DIR, 'images')
    def __init__(self) -> None:
        super(chatbotAssist, self).__init__()
        self.assist_init()

    def init(self):
        super(chatbotAssist, self).init()
        self.assist_init()

    def assist_init(self):
        '''
        初始化成员变量：助手、对话线程、对话数据库
        '''
        self._assistant = None
        self._thread = None
        self._thread_messages = []
        self._vector_stores = []

    def assistant_ready(self):
        return self._assistant is not None

    def assistant_name(self):
        if not self.assistant_ready(): return 'no assistant'
        return self._assistant.name

    def init_assistant(self, name, instruction, tools):
        '''
        tools: [{"type": "code_interpreter"}, {"type": "file_search"}]
        '''
        # self._assistant = self._client.beta.assistants.create(
        #                     name=name,
        #                     instructions=instruction,
        #                     tools=tools,
        #                     model=self._model, #目前由环境变量指定
        #                     timeout=15,
        #                 )

        self._assistant = dmy_ass()
        self._assistant.name = name
        self._assistant.id = name
        self._assistant.instruction = instruction
        self._assistant.tools = tools


    def assistant_prop(self):
        if self._client is None or self._assistant is None:
            return None

        # self._assistant = self._client.beta.assistants.retrieve(self._assistant.id)

        return json.loads(self._assistant.model_dump_json(indent=2))

    def init_thread(self, infer_size=32):
        '''
        thread实质上是助手和用户之间对话会话的记录。
        '''
        self._thread = self._client.beta.threads.create(
            messages=self._messages[-infer_size:]
        )
        self._thread_messages = parse_thread_messages(self._client, self._thread, self.assistant_name())

        print(json.dumps(self._thread_messages, indent=4))

    def with_file(self, vid_list):
        self._assistant = self._client.beta.assistants.update(
                                                                assistant_id=self._assistant.id,
                                                                tools=[{"type": "file_search"}],
                                                                tool_resources={"file_search": {"vector_store_ids": vid_list}},
                                                                )
        self._thread = self._client.beta.threads.update(
                                                            thread_id=self._thread.id,
                                                            tool_resources={"file_search": {"vector_store_ids": vid_list}},
                                                        )

    def sync_user_msg(self, infer_size=5):
        #线程消息必须是bot消息的子集
        size_thread = len(self._thread_messages)
        size_msg = len(self._messages)

        need_reinit = False
        sync_id = -(len(self._messages)+1)
        if size_msg<size_thread:
            #已有消息被删除
            need_reinit = True
        elif size_thread==0:
            #线程未初始化
            need_reinit = size_msg!=0
        else:
            need_reinit, sync_id = search_thread_msg(self._messages, self._thread_messages)

        if not need_reinit:
            for msg in self._messages[len(self._messages)+1+sync_id:]:
                message = self._client.beta.threads.messages.create(
                                                                    thread_id=self._thread.id,
                                                                    role=msg["role"],
                                                                    content=msg["content"], # Replace this with your prompt
                                                                    )
                responses = parse_thread_message(message, self._client, self._thread, self.assistant_name())
                self._thread_messages.extend(responses)

        if len(self._thread_messages)<infer_size and len(self._messages)>=infer_size:
            need_reinit = True

        if need_reinit:
            self.init_thread(infer_size=infer_size)

    def generate_response(self, infer_size=5):
        '''
        返回 消息列表或抛出异常
        '''
        if not self.assistant_ready():
            raise Exception('助手未初始化，请【列出助手】-【选择助手】')

        self.sync_user_msg(infer_size=infer_size)

        print('waiting openai...')
        
        run = self._client.beta.threads.runs.create(
                                                    thread_id=self._thread.id,
                                                    assistant_id=self._assistant.id
                                                    )

        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = self._client.beta.threads.runs.retrieve(
                thread_id=self._thread.id,
                run_id=run.id
            )

        print(f'openai answered {run.status}')

        responses = []
        if run.status == 'completed':
            thread_messages = self._client.beta.threads.messages.list(
                                                                thread_id =self._thread.id
                                                            )
            
            if len(thread_messages.data)==0 or thread_messages.data[0].role!='assistant':
                raise Exception(f'Not assistant message:\n{thread_messages.model_dump_json(indent=4)}')

            responses = parse_thread_message(thread_messages.data[0], self._client, self._thread, self.assistant_name())

            self._thread_messages.extend(responses)


        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            print(run.status)
        else:
            print(run.status)
        
        return responses
    
    # def on_user_input(self, text):
    #     print(text)
    #     super(chatbotAssist, self).on_user_input(text)
    #     print('test:')

    #     #完全一致
    #     if len(self.messages())>1:
    #         print('test A------------')
    #         thread_msg = [x for x in self.messages()]
    #         bot_msg = [x for x in self.messages()]
    #         unmath, sync_id = search_thread_msg(bot_msg, thread_msg)
    #         assert(not unmath and sync_id==-1 and len(self._messages[len(self._messages)+sync_id+1:])==0)

    #     #thread少1个
    #     if len(self.messages())>2:
    #         print('test B------------')
    #         thread_msg = [x for x in self.messages()[:-1]]
    #         bot_msg = [x for x in self.messages()]
    #         unmath, sync_id = search_thread_msg(bot_msg, thread_msg)
    #         assert(not unmath and sync_id==-2 and len(self._messages[len(self._messages)+sync_id+1:])==1)

    #         print('test C------------')
    #         thread_msg = [x for x in self.messages()[1:]]
    #         bot_msg = [x for x in self.messages()]
    #         unmath, sync_id = search_thread_msg(bot_msg, thread_msg)
    #         assert(not unmath and sync_id==-1 and len(self._messages[len(self._messages)+sync_id+1:])==0)

    #     #thread少2个
    #     if len(self.messages())>3:
    #         print('test D------------')
    #         thread_msg = [x for x in self.messages()[:-2]]
    #         bot_msg = [x for x in self.messages()]
    #         unmath, sync_id = search_thread_msg(bot_msg, thread_msg)
    #         assert(not unmath and sync_id==-3 and len(self._messages[len(self._messages)+sync_id+1:])==2)
    #     print('================================================================== over')



    def create_vecotr_store(self, name):
        vector_store = self._client.beta.vector_stores.create(name=name)
        return vector_store.id

    def list_vector_stores(self, online=False):
        if online:
            self._vector_stores = []
            self._vector_stores = self._client.beta.vector_stores.list()
            for vs in self._vector_stores:
                print("* ", vs.name, datetime.datetime.fromtimestamp(vs.created_at), vs.id, vs.file_counts.completed, vs.status)
        return self._vector_stores

    def find_vector_store_id(self, name, file_nb=-1, online=False):
        self.list_vector_stores(online=online)
        for vs in self._vector_stores:
            if vs.name==name and vs.status=='completed' and (file_nb<0 or vs.file_counts.completed==file_nb):
                return vs.id
        return None

    def upload_file(self, name, data):
        name = os.path.split(name)[-1]

        for online in [False, True]:
            vid = self.find_vector_store_id(name, file_nb=1, online=online)
            if vid:
                print(f'找到 文件在 {vid}')
                return

        vid = self.create_vecotr_store(name)

        file_batch = self._client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vid, files=[data]
        )
        while file_batch.status in ['in_progress']:
            time.sleep(1)
            file_batch = self._client.beta.vector_stores.file_batches.retrieve(
                vector_store_id=vid,
            )
        print(file_batch.status)
        print(file_batch.file_counts)

        if file_batch.status=='completed':
            self._vector_stores.append(self._client.beta.vector_stores.retrieve(vector_store_id = vid))

        raise Exception(f'upload {file_batch.status}')
