import os
import json
import datetime
import time

from streamlit.runtime.metrics_util import F
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
        print(f'init {self.messages()}')

    def assist_init(self):
        '''
        初始化时删除旧助手
        '''
        self._assistant = None
        self._thread = None
        self._message_file = None
        self._vid = None

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

    def on_user_input(self, text, with_file=False):
        if with_file and self._vid:
            # print(self._assistant.tool_resources.file_search)
            self._assistant = self._client.beta.assistants.update(
                                                                    assistant_id=self._assistant.id,
                                                                    tools=[{"type": "file_search"}],
                                                                    tool_resources={"file_search": {"vector_store_ids": [self._vid]}},
                                                                    )
            # print(self._assistant.tool_resources.file_search)
            # print(self._thread.tool_resources.file_search)
            # self._thread = self._client.beta.threads.update(
            #                                                     thread_id=self._thread.id,
            #                                                     tool_resources={"file_search": {"vector_store_ids": [self._vid]}},
            #                                                 )
            # print(self._thread.tool_resources.file_search)
            self._thread = self._client.beta.threads.create()

        if self.assistant_ready():
            # attachments = None
            # if with_file and self._message_file is not None:
            #     attachments.=[
            #         { "file_id": self._message_file.id, "tools": [{"type": "file_search"}] }
            #     ]
            message = self._client.beta.threads.messages.create(
                                                                thread_id=self._thread.id,
                                                                role='user',
                                                                content=text, # Replace this with your prompt
                                                                # attachments=attachments,
                                                                )
            # print(attachments)
        super(chatbotAssist, self).on_user_input(text)

    def generate_response(self, infer_size=5):
        '''
        返回消息列表或抛出异常
        '''
        if not self.assistant_ready():
            raise Exception('助手未初始化，请【列出助手】-【选择助手】')

        messages = self._client.beta.threads.messages.list(
                                                            thread_id =self._thread.id
                                                        )
        # data = json.loads(messages.model_dump_json(indent=2))
        if messages.data[0].role!='user':
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
            # data = json.loads(messages.model_dump_json(indent=2))
            # with open('history/debug/ass_messages.json', 'w+') as dbgf:
            #     dbgf.write(messages.model_dump_json(indent=2))
            
            if messages.data[0].role!='assistant':
                raise Exception('Not assistant message')
            for content in messages.data[0].content:
                if content.type=='text':

                    message_content = content.text
                    annotations = message_content.annotations
                    citations = []
                    for index, annotation in enumerate(annotations):
                        message_content.value = message_content.value.replace(
                            annotation.text, f"[{index}]"
                        )
                        if file_citation := getattr(annotation, "file_citation", None):
                            cited_file = self._client.files.retrieve(file_citation.file_id)
                            citations.append(f"[{index}] {cited_file.filename}")

                    text = message_content.value.strip() + "\n" + '\n'.join(citations)
                    responses.append(
                                        {
                                            "role":"assistant",
                                            "content":text,
                                            "assistant_type":self.assistant_name(),
                                            "type":'text',
                                        }
                                    )

                elif content.type=='image_file':
                    image_file_id = content.image_file.file_id
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

        elif run.status == 'requires_action':
            # the assistant requires calling some functions
            # and submit the tool outputs back to the run
            print(run.status)
        else:
            print(run.status)
        
        return responses
    
    def create_vecotr_store(self, name):
        vid = self.find_vector_store_id(name, file_nb=1)
        if vid is None:
            vector_store = self._client.beta.vector_stores.create(name=name)
            vid = vector_store.id
        return vid

    def list_vector_stores(self):
        print('----')
        vector_stores = []
        try:
            vector_stores = self._client.beta.vector_stores.list()
            for vs in vector_stores:
                print("* ", vs.name, datetime.datetime.fromtimestamp(vs.created_at), vs.id, vs.file_counts.completed)
        finally:
            return vector_stores

    def find_vector_store_id(self, name, file_nb=-1):
        vector_stores = self.list_vector_stores()
        for vs in vector_stores:
            if vs.name==name and (file_nb<0 or vs.file_counts.completed==file_nb):
                return vs.id
        return None

    def upload_file(self, name, data, append):
        name = os.path.split(name)[-1]
        print(f'{name}, cur_vid={self._vid}, append={append}')

        if not append:
            self._vid = self.find_vector_store_id(name, file_nb=1)
            if self._vid:
                print(f'找到 文件在 {self._vid}')
                return

        if not self._vid:
            self._vid = self.create_vecotr_store(name)

        # self._message_file = self._client.files.create(
        #     file=data, purpose="assistants"
        # )
        # print(self._message_file.id)

        file_batch = self._client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=self._vid, files=[data]
        )
        while file_batch.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            file_batch = self._client.beta.vector_stores.file_batches.retrieve(
                vector_store_id=self._vid,
            )
        print(file_batch.status)
        print(file_batch.file_counts)