# simple_chat_bot
chat bot: AzureOpenAI + streamlit

## install

```sh
## clone the repo:
git clone https://github.com/chinsaiki/simple_chat_bot.git

## create envirment, example with anaconda:
conda create -n chatbot python=3.9
conda activate chatbot

cd simple_chat_bot

## install modules:
pip install -r requirements.txt 
#for those in China(用国内源): 
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

## set AzureOpenAI parameters:
cp .env.example .env  #change 'cp' to 'copy' in Windows
#EDIT .env

## run:
streamlit run main.py
```

## demo

![demo](demo.png)

