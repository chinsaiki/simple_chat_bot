import os
import json
import datetime
import time
from openai.types.beta import Thread
from openai.types.beta.threads import Message
from openai import AzureOpenAI
from typing import List
from collections import OrderedDict

from chatbot import chatbot

ASSIST_NAME = 'assist_name'
ASSIST_INST = 'assist_instruction'


## 以缩进形式打印任意字典
def pretty(value, htchar='\t', lfchar='\n', indent=0):
    nlch = lfchar + htchar * (indent + 1)
    if isinstance(value, (dict, OrderedDict)):
        keys = list(value.keys())
        if not isinstance(value, OrderedDict):
            keys = sorted(keys)
        items = [
            nlch + repr(key) + ': ' + pretty(value[key], htchar, lfchar, indent + 1)
            for key in keys
        ]
        return '{%s}' % (','.join(items) + lfchar + htchar * indent)
    elif type(value) is list:
        items = [
            nlch + pretty(item, htchar, lfchar, indent + 1)
            for item in value
        ]
        return '[%s]' % (','.join(items) + lfchar + htchar * indent)
    elif type(value) is tuple:
        items = [
            nlch + pretty(item, htchar, lfchar, indent + 1)
            for item in value
        ]
        return '(%s)' % (','.join(items) + lfchar + htchar * indent)
    else:
        return repr(value)

def parse_thread_message_all(client:AzureOpenAI, thread:Thread, assistant_name:str):
    if client is None or thread is None:
        return {'ERROR': f'client={client}, thread={thread}'}
    thread_messages = client.beta.threads.messages.list(
                                                        thread_id =thread.id
                                                    )
    message_infos = []
    for message in thread_messages.data[::-1]: #data[0]是最新的消息
        message_infos.extend(parse_thread_message_single(message, client, thread, assistant_name))

    return message_infos

def parse_thread_message_single(thread_message:Message, client:AzureOpenAI, thread:Thread, assistant_name:str ):
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

            text = message_content.value.strip()
            if len(citations):
                text += "\n" + '\n'.join(citations)
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
    # print(f'search_thread_msg size_msg={smax} size_thread={size}')
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
        self.thread_init()

    def assist_init(self):
        '''
        初始化成员变量：助手、对话线程、对话数据库
        '''
        self._assistant = None
        self._vector_stores = []

    def thread_init(self):
        self._thread = None
        self._thread_messages = []

    def assistant_ready(self):
        return self._assistant is not None

    def assistant_name(self):
        if not self.assistant_ready(): return 'no assistant'
        return self._assistant.name

    def setup_assistant(self, name, instruction, tools):
        '''
        tools: [{"type": "code_interpreter"}, {"type": "file_search"}]
        '''
        self.setup_client(force=False)
        TimeOut = 30
        self._assistant = self._client.beta.assistants.create(
                            name=name,
                            instructions=instruction,
                            tools=tools,
                            model=self._model, #目前由环境变量指定
                            timeout=TimeOut,
                        )

        # self._assistant = dmy_ass()
        # self._assistant.name = name
        # self._assistant.id = name
        # self._assistant.instruction = instruction
        # self._assistant.tools = tools


    def assistant_prop(self):
        if self._client is None or self._assistant is None:
            cli_is_None = ' "client is None"' if self._client is None else ''
            ass_is_None = ' "assistant is None"' if self._assistant is None else ''
            return {'ERROR':f'No assistant for{cli_is_None}{ass_is_None}.'}

        # self._assistant = self._client.beta.assistants.retrieve(self._assistant.id)

        return json.loads(self._assistant.model_dump_json(indent=2))

    def assistant_prop_text(self):
        dic = self.assistant_prop()
        return pretty(dic)

    def setup_thread(self, infer_size=32):
        '''
        thread实质上是助手和用户之间对话会话的记录。
        '''
        self._thread = self._client.beta.threads.create(
            messages=self.chat_messages[-infer_size:],
            timeout=30
        )
        self._thread_messages = parse_thread_message_all(self._client, self._thread, self.assistant_name())

        # print(json.dumps(self._thread_messages, indent=4))

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

    def delet_last_message(self, nb):
        super(chatbotAssist, self).delet_last_message(nb)
        if nb>0:
            self._thread_messages = [] #清空线程消息
            print('thread messages cleared')
    def sync_user_msg(self, infer_size=5):
        '''
        用于保证最后 infer_size 是一致的
        '''
        #线程消息必须是bot消息的子集
        size_thread = len(self._thread_messages)
        size_msg = len(self._messages)

        need_reinit = False
        sync_id = -(len(self._messages)+1)
        if size_msg<size_thread:
            #已有消息被删除
            need_reinit = True
            print('要求重建：已有消息被删除')
        elif size_thread==0:
            #线程消息为空
            need_reinit = size_msg!=0
            print('要求重建：线程消息为空')
        else:
            need_reinit, sync_id = search_thread_msg(self._messages, self._thread_messages)
            if need_reinit:
                print('要求重建：search_thread_msg')
                with open('debug/thread_msg.json', 'w+') as f:
                    json.dump(self._thread_messages, f)
                with open('debug/msg.json', 'w+') as f:
                    json.dump(self._messages, f)

        if not need_reinit:
            for msg in self._messages[len(self._messages)+1+sync_id:]:
                message = self._client.beta.threads.messages.create(
                                                                    thread_id=self._thread.id,
                                                                    role=msg["role"],
                                                                    content=msg["content"], # Replace this with your prompt
                                                                    )
                responses = parse_thread_message_single(message, self._client, self._thread, self.assistant_name())
                self._thread_messages.extend(responses) #至此两套messages应该等长
        
        if not need_reinit:
            if len(self._thread_messages)<infer_size and len(self._messages)>len(self._thread_messages):
                print('要求重建：补充到infer')
                need_reinit = True

        if need_reinit:
            print(f'重建 tread({infer_size})')
            self.setup_thread(infer_size=infer_size)
            print('done')

    def assistant_response(self, infer_size=5):
        '''
        返回 消息列表或抛出异常
        '''
        if not self.assistant_ready():
            return '助手未初始化，请【跳到顶部】->【控制】->【选择助手及参数】->【应用】'
        infer_size = max(infer_size, 1)

        self.sync_user_msg(infer_size=infer_size)

        print('waiting openai... ')
        
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

            responses = parse_thread_message_single(thread_messages.data[0], self._client, self._thread, self.assistant_name())

            self._thread_messages.extend(responses)


        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            print(run.status)
        else:
            print(run.status)
        
        return responses

    def generate_response(self, infer_size=5):
        return self.assistant_response(infer_size)

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

    def get_thread_message_text(self, online=False):
        if not online:
            return pretty(self._thread_messages, lfchar='\n\n')
        
        return pretty(parse_thread_message_all(self._client, self._thread, '助手名称占位符'), lfchar='\n\n')

    def debug_info(self):
        thread_msg = self.get_thread_message_text(online=False)
        local_msg = pretty(self._messages, lfchar='\n\n')
        assist_info = pretty(json.loads(self._assistant.model_dump_json(indent=2)), lfchar='\n\n') if self._assistant is not None else 'Assistant is None'
        thread_info = pretty(json.loads(self._thread.model_dump_json(indent=2)), lfchar='\n\n') if self._thread is not None else 'Thread is None'
        return  "\n\n".join([
                            assist_info,
                            thread_info,
                            thread_msg,
                            local_msg
                        ])