from typing_extensions import Literal
from typing import List, Union, Optional

class chat_message():
    '''
    为了便于展示对话消息。
    '''

    role: Literal["assistant", "user"]

    content: str
    '''
    message text if content_type is 'text'.

    image_file path if content_type is 'image_file'
    '''

    content_type: Optional[Literal["text", "image_file"]] = None
    '''
    None = text
    '''

    assistant_name: Optional[str] = None

    assistant_icon: Optional[str] = None

    tools: Optional[str] = None

    files: Optional[str] = None

    # vector_stores: Optional[str] = None
    

    def load(data):
        if isinstance(data, chat_message): return data
        msg = chat_message()
        msg.role = data['role']
        msg.content = data['content']
        if 'content_type' in data: msg.content_type = data['content_type']
        if 'assistant_name' in data: msg.assistant_name = data['assistant_name']
        if 'assistant_icon' in data: 
            msg.assistant_icon = data['assistant_icon']
        elif 'assistant_name' in data:
            msg.assistant_icon = '🤖' #🛸
        if 'tools' in data: msg.tools = data['tools']
        if 'files' in data: msg.files = data['files']
        if msg.files is not None and msg.assistant_icon is not None:
            msg.assistant_icon += '📑' #📖
        return msg