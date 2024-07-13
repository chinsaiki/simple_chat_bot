import os
import json
import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv
import time
from collections import OrderedDict
import sys
from chat_message import chat_message
import shutil

class chatbot:
    env_inited = False
    azure_server = {}

    if hasattr(sys, '_MEIPASS'):
        ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(sys.executable))))
    else:
        ROOT = os.path.dirname(os.path.abspath(__file__))
    HISTORY_DIR = os.path.join(ROOT, 'history')  #存放编译阅读的md文件
    PROFILE_DIR = os.path.join(ROOT, 'profile')  #存放会话配置文件
    PROFILE_TRASH_DIR = os.path.join(PROFILE_DIR, 'trash') #删除的会话配置文件
    ENV_FILE = os.path.join(ROOT, '.env')

    def __init__(self) -> None:
        if not chatbot.env_inited:
            chatbot.force_load_env()
            chatbot.env_inited = True

        self.init()

    def init(self):
        '''
        初始化所有成员变量：初始化时戳、清空消息、清空Azure客户端和模型。
        '''
        self._timestamp = '{}'.format(datetime.datetime.now()).replace('-', '_').replace(':', '_').replace(' ','_')
        self._messages = []
        self._history_handler = None
        self._client = None
        self._model = None

    def setup_client(self, force):
        '''
        搭建Azure客户端，第一次向服务器发送请求前执行一次。
        '''
        if self._client is not None and not force:
            return

        for env_var in ['API_KEY', 'ENDPOINT', 'OPENAI_GPT_DEPLOYMENT_NAME']:
            if os.getenv(env_var) is None:
                raise Exception(f'{env_var} not found in {chatbot.ENV_FILE}')

        api_key = os.getenv("API_KEY")  # azure_server['key']
        api_version = "2024-05-01-preview"
        azure_endpoint = os.getenv("ENDPOINT") # azure_server['endpoint']
        self._client = AzureOpenAI(
                        api_key=api_key,  
                        api_version=api_version,
                        azure_endpoint = azure_endpoint
                    )
        self._model = os.getenv("OPENAI_GPT_DEPLOYMENT_NAME") # azure_server['gpt']

    def id(self):
        '''
        时戳作为bot(对话)的id
        '''
        return self._timestamp #加载历史对话后可能改变

    def summary(self, char_lmt=64):
        '''
        话题总结。
        '''
        summary = 'null'
        if len(self._messages)>0:
            summary = self._messages[0]['content'].strip()[:char_lmt]
        return summary


    def profile(self):
        '''
        当前对话属性。
        '''
        export = {
            'messages' : self._messages,
            'timestamp': self._timestamp,
            'summary' : self.summary(),
        }
        return export

    def messages(self):
        '''
        返回以展示为目的的message list
        '''
        return self._messages

    def delet_last_message(self, nb):
        self._messages = self._messages[:-nb]
        
    def load_profile_data(self, profile):
        '''
        加载历史对话属性。
        '''
        if 'messages' in profile: self._messages = profile['messages']
        if 'timestamp' in profile: self._timestamp = profile['timestamp']
        self._history_handler = None

    def save_profile_to_file(self):
        if len(self._messages)==0: # null conversation, do not save
            return

        if not os.path.exists(chatbot.PROFILE_DIR):
            os.mkdir(chatbot.PROFILE_DIR)
        file_path = os.path.abspath(os.path.join(chatbot.PROFILE_DIR, f'chat_{self._timestamp}.json'))
        with open(file_path, 'w+', encoding='utf-8') as f:
            json.dump(self.profile(), f, indent=4)

    def make_history_handler(self):
        if not os.path.exists(chatbot.HISTORY_DIR):
            os.mkdir(chatbot.HISTORY_DIR)

        file_path = os.path.abspath(os.path.join(chatbot.HISTORY_DIR, f'chat_{self._timestamp}.md'))
        self._history_handler = open(file_path, 'a+', encoding='utf-8')

    def generate_response(self, infer_size=5):
        '''
        return text:str
        '''
        self.setup_client(force=False)

        print('waiting openai...')
        completion = self._client.chat.completions.create(
            model=self._model, # model = "deployment_name"
            messages = self._messages[-infer_size:],
            temperature=0.7,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False,
            timeout=30
        )
        print('openai answered')

        message = completion.choices[0].message.content
        if isinstance(message, str):
            message = message.strip()
        
        return message
    
    def generate_event(self, infer_size=5):
        '''
        return Stream
        '''
        self.setup_client(force=False)

        response = self._client.chat.completions.create(
            model=self._model, # model = "deployment_name"
            messages = self._messages[-infer_size:],
            temperature=0.7,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=True,
            timeout=30
        )
        
        return response

    def generate_stream_response(self, placeholder, infer_size=5):
        '''
        streamly write response to placeholder.

        return text:str
        '''
        message = ''
        response = self.generate_event(infer_size=infer_size) 
        if response is None: #不支持事件
            return self.generate_response(infer_size=infer_size)
        collected_messages = []

        for chunk in response:
            if len(chunk.choices):
                chunk_message = chunk.choices[0].delta.content
                if chunk_message is not None:
                    collected_messages.append(chunk_message)
                    message = ''.join(collected_messages)
                    placeholder.markdown(message)
                else:
                    break
            time.sleep(0.03)

        return message


    def dmy_response(self, blocking=0):
        time.sleep(blocking)
        message = "this is dmy resopnse of '''" + self._messages[-1]['content'] + "'''"
        raise Exception('test broken')
        return message

    def on_history_user_input(self, text):
        if self._history_handler is None:
            self.make_history_handler()
        self._history_handler.write(f'>###### User:\n\n{text}\n\n...... Waiting AI ......\n\n')
        self._history_handler.flush()

    def on_user_input(self, text):
        self._messages.append(
            {
                "role":"user",
                "content":text
            }
        )

        self.on_history_user_input(text)

    def on_history_text(self, text):
        if self._history_handler is None:
            self.make_history_handler()
        self._history_handler.write(f'>###### AI:\n\n{text}\n\n-----------------------------------------------------------\n\n')
        self._history_handler.flush()

    def on_history_image(self, file_path):
        if self._history_handler is None:
            self.make_history_handler()
        if sys.platform == "win32": file_path = file_path.replace("\\", "/")
        self._history_handler.write(f'>###### AI:\n\n![{file_path}]({file_path})\n\n-----------------------------------------------------------\n\n')
        self._history_handler.flush()

    def on_ai_response(self, message):
        '''
        message: str|list

        当message是list时，元素需为以下map
                {
                    "role":"assistant"|"user",
                    "content": str,
                    "content_type":'text'|'image_file'|None,
                    "assistant_name":None|str,
                }
        '''
        if isinstance(message, list):
            self._messages.extend(message)
            for m in message:
                if m['content_type']=='image_file':
                    self.on_history_image(m["content"])
                elif m['content_type']=='text':
                    self.on_history_text(m["content"])
                else:
                    raise Exception(f'Not support content_type={m["content_type"]}')
        else:
            self._messages.append(
                {
                    "role":"assistant",
                    "content":message,
                    "content_type":'text',
                    "assistant_name":None,
                }
            )
            self.on_history_text(message)

    @staticmethod
    def force_load_env():
        load_dotenv(chatbot.ENV_FILE)


    #just for future
    @staticmethod
    def load_azure(resource_name, config_file='azure_openai.json'):
        with open(config_file, 'r') as f:
            config = json.load(f)
            if resource_name not in config:
                raise Exception(f'resource {resource_name} not found in {config_file}')
            chatbot.azure_server = config[resource_name]
            
    @staticmethod
    def list_profiles(key_size=32):
        profiles = OrderedDict()
        for fname in os.listdir(chatbot.PROFILE_DIR):
            fname = os.path.join(chatbot.PROFILE_DIR, fname)
            if not os.path.isfile(fname):continue
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                key = data['summary'][:key_size]
                if len(data['summary'])>len(key): key += '...'
                if key!='null':
                    in_key = key
                    r = 1
                    while in_key in profiles:
                        in_key = f'{key}[{r}]'
                        r += 1
                    profiles[in_key] = {
                        'data':data,
                        'fname': fname
                    }
        return profiles

    @staticmethod
    def delete_profile(fname):
        '''
        从profile目录移到profile/trash目录
        '''
        if not os.path.exists(fname):
            raise Exception(f'delete {fname}: file not exist')

        try:
            if not os.path.exists(chatbot.PROFILE_TRASH_DIR):
                os.mkdir(chatbot.PROFILE_TRASH_DIR)

            source_path, file_name = os.path.split(fname)
            if os.path.abspath(source_path)!=os.path.abspath(chatbot.PROFILE_DIR):
                raise Exception(f'{fname} not in profile folder.')

            # 构建目标文件的完整路径
            destination_path = os.path.join(chatbot.PROFILE_TRASH_DIR, file_name)
            shutil.move(fname, destination_path)
        except Exception as e:
            print(f"Error moving file: {e}")
            raise e

