import os
import json
import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv
import time
from collections import OrderedDict

class chatbot:
    env_inited = False
    azure_server = {}

    ROOT = os.path.dirname(os.path.abspath(__file__))
    HISTORY_DIR = os.path.join(ROOT, 'history')
    PROFILE_DIR = os.path.join(ROOT, 'profile')

    def __init__(self) -> None:
        if not chatbot.env_inited:
            chatbot.force_load_env()
            chatbot.env_inited = True

        self.init()

    def init(self, profile=None):
        api_key = os.getenv("API_KEY")  # azure_server['key']
        api_version = "2024-02-15-preview"
        azure_endpoint = os.getenv("ENDPOINT") # azure_server['endpoint']
        self._client = AzureOpenAI(
                        api_key=api_key,  
                        api_version=api_version,
                        azure_endpoint = azure_endpoint
                    )
        self._messages = [] if profile is None else profile['messages']
        self._model = os.getenv("OPENAI_GPT_DEPLOYMENT_NAME") # azure_server['gpt']

        self._timestamp = '{}'.format(datetime.datetime.now()).replace('-', '_').replace(':', '_').replace(' ','_') if profile is None else profile['timestamp']

        self.make_history_handler()

    def make_history_handler(self):
        if not os.path.exists(chatbot.HISTORY_DIR):
            os.mkdir(chatbot.HISTORY_DIR)

        self._current_history = os.path.abspath(os.path.join(chatbot.HISTORY_DIR, f'chat_{self._timestamp}.md'))
        self._history_handler = open(self._current_history, 'a+', encoding='utf-8')
        self._history_handler.write('# *Init chatbot*\n\n')

    def save_profile(self):
        if len(self._messages)==0: # null conversation, do not save
            return
        
        profile_folder = 'profile'
        if not os.path.exists(profile_folder):
            os.mkdir(profile_folder)
        current_profile = os.path.abspath(os.path.join(profile_folder, f'chat_{self._timestamp}.json'))
        with open(current_profile, 'w+', encoding='utf-8') as f:
            json.dump(self.profile(), f, indent=4)


    def generate_response(self, infer_size=5):
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

    
    def dmy_response(self, blocking=0):
        time.sleep(blocking)
        message = "this is dmy resopnse of '''" + self._messages[-1]['content'] + "'''"
        return message

    def on_user_input(self, text):
        self._messages.append(
            {
                "role":"user",
                "content":text
            }
        )

        self._history_handler.write(f'>###### User:\n\n{text}\n\n...... Waiting AI ......\n\n')
        self._history_handler.flush()

    def on_ai_response(self, text):
        self._messages.append(
            {
                "role":"assistant",
                "content":text
            }
        )
        
        self._history_handler.write(f'>###### AI:\n\n{text}\n\n-----------------------------------------------------------\n\n')
        self._history_handler.flush()

    def messages(self):
        return self._messages


    def profile(self):
        export = {
            'messages' : self._messages,
            'timestamp': self._timestamp,
        }

        summary = 'null'
        if len(self._messages)>0:
            summary = self._messages[0]['content'].strip()[:64]

        export['summary'] = summary

        return export

    @staticmethod
    def force_load_env():
        load_dotenv()


    #just for future
    @staticmethod
    def load_azure(resource_name, config_file='azure_openai.json'):
        with open(config_file, 'r') as f:
            config = json.load(f)
            if resource_name not in config:
                raise Exception(f'resource {resource_name} not found in {config_file}')
            chatbot.azure_server = config[resource_name]
            
    @staticmethod
    def list_profiles():
        profiles = OrderedDict()
        for fname in os.listdir(chatbot.PROFILE_DIR):
            fname = os.path.join(chatbot.PROFILE_DIR, fname)
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                key = data['summary'][:32]
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