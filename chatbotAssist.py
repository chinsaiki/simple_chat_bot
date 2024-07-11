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
        self._vector_stores = []

    def assist_init(self):
        '''
        初始化时删除旧助手
        '''
        self._assistant = None
        self._thread = None
        self._message_file = None

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
                            timeout=30,
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

    def sync_user_msg(self):
        messages = self._client.beta.threads.messages.list(
                                                            thread_id =self._thread.id
                                                        )
        # data = json.loads(messages.model_dump_json(indent=2))
        if messages.data[0].role!=self._messages[-1]["role"] or messages.data[0].content[0].text.value!=self._messages[-1]["content"]:
            message = self._client.beta.threads.messages.create(
                                                                thread_id=self._thread.id,
                                                                role=self._messages[-1]["role"],
                                                                content=self._messages[-1]["content"], # Replace this with your prompt
                                                                )


    def generate_response(self, infer_size=5):
        '''
        返回 消息列表或抛出异常
        '''
        if not self.assistant_ready():
            raise Exception('助手未初始化，请【列出助手】-【选择助手】')

        self.sync_user_msg()

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
                                            "tool_resources":self._thread.tool_resources.model_dump_json(indent=2),
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
                                            "tool_resources":self._thread.tool_resources.model_dump_json(indent=2),
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