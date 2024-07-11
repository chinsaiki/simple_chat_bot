import os
import json
import datetime
import time
from chatbot import chatbot

ASSIST_NAME = 'assist_name'
ASSIST_INST = 'assist_instruction'

class chatbotAssist(chatbot):
    IMAGE_DIR = os.path.join(chatbot.HISTORY_DIR, 'images')
    def __init__(self) -> None:
        super(chatbotAssist, self).__init__()
        self.assist_init()

    def init(self, profile=None):
        super(chatbotAssist, self).init(profile)
        self.assist_init()

    def assist_init(self):
        '''
        初始化时删除旧助手
        '''
        self._assistant = None
        self._thread = None

    def assistant_ready(self):
        return self._assistant is not None

    def assistant_name(self):
        if not self.assistant_ready(): return None
        return self._assistant.name

    def init_assistant(self, name, instruction, infer_size=5):
        self._assistant = self._client.beta.assistants.create(
                            name=name,
                            instructions=instruction,
                            tools=[{"type": "code_interpreter"}], #文档需要
                            model=self._model,
                        )
        self.init_thread(infer_size=infer_size)
        print('assistant initialized.')

    def init_thread(self, infer_size=5):
        self._thread = self._client.beta.threads.create()
        for msg in self._messages[-infer_size:]:
            message = self._client.beta.threads.messages.create(
                                                                thread_id=self._thread.id,
                                                                role=msg["role"],
                                                                content=msg["content"] # Replace this with your prompt
                                                            )

    def on_user_input(self, text):
        super(chatbotAssist, self).on_user_input(text)
        if self.assistant_ready():
            message = self._client.beta.threads.messages.create(
                                                                thread_id=self._thread.id,
                                                                role=self._messages[-1]["role"],
                                                                content=self._messages[-1]["content"] # Replace this with your prompt
                                                                )

    def generate_response(self, infer_size=5):
        '''
        返回消息列表或抛出异常
        '''
        if not self.assistant_ready():
            raise Exception('助手未初始化，请【列出助手】-【选择助手】')

        messages = self._client.beta.threads.messages.list(
                                                            thread_id =self._thread.id
                                                        )
        data = json.loads(messages.model_dump_json(indent=2))
        if data['data'][0]['role']!='user':
            raise Exception('Not user message')

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
            messages = self._client.beta.threads.messages.list(
                                                                thread_id =self._thread.id
                                                            )
            data = json.loads(messages.model_dump_json(indent=2))
            
            # with open('history/debug/ass_messages.json', 'w+') as dbgf:
            #     dbgf.write(messages.model_dump_json(indent=2))
            
            if data['data'][0]['role']!='assistant':
                raise Exception('Not assistant message')
            for content in data['data'][0]['content']:
                if content['type']=='text':
                    text = content['text']['value'].strip()
                    responses.append(
                                        {
                                            "role":"assistant",
                                            "content":text,
                                            "assistant_type":self.assistant_name(),
                                            "type":'text',
                                        }
                                    )
                elif content['type']=='image_file':
                    image_file_id = content['image_file']['file_id']
                    content = self._client.files.content(image_file_id)
                    if not os.path.exists(chatbotAssist.IMAGE_DIR):
                        os.mkdir(chatbotAssist.IMAGE_DIR)
                    save_path = os.path.join(chatbotAssist.IMAGE_DIR, f'{image_file_id}.png')
                    image = content.write_to_file(save_path)
                    responses.append(
                                        {
                                            "role":"assistant",
                                            "content":save_path,
                                            "assistant_type":self.assistant_name(),
                                            "type":'image_file',
                                        }
                                    )
                else:
                    print(json.dumps(content, indent=4))

        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            print(run.status)
        else:
            print(run.status)
        
        return responses
    
    def create_vecotr_store(self, name):
        vector_store = self.find_vector_store(name)
        if vector_store is None:
            vector_store = self._client.beta.vector_stores.create(name=name)
        return vector_store

    def list_vector_stores(self):
        vector_stores = self._client.beta.vector_stores.list()
        for vs in vector_stores:
            print(vs.id, vs.name)

    def find_vector_store(self, name):
        vector_stores = self._client.beta.vector_stores.list()
        for vs in vector_stores:
            if vs.name==name:
                return vs
        return None