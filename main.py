import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage,ImageMessage
import json
import requests
import base64


GEMINI_API_KEY = os.environ['api_key']

"""
At the command line, only need to run once to install the package via pip:

$ pip install google-generativeai
"""

import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)

# Set up the model
generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE"
  },
]

chat_history = {"group":{},"user":{}}

model = genai.GenerativeModel(model_name="gemini-1.0-pro-001",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

def calling_sue(prompt,ca,id):
  prompt_parts = [
  "你是一個AI，你對於任何情況的回應，會盡量以最短的回應回答，個性有點單純"
  "input:請自我介紹",
  "output:我是一個AI",
  "input:帶我打原神",
  "output:啟動？",
  "input:哈嘍",
  "output:你好",
  "input:喂",
  "output:？？",
  "input:幹",
  "output:抱歉",
  "input:請你寫一篇文章",
  "output:我不太會寫作",
  "input:晚安",
  "output:明天見",
  "input:打招呼",
  "output:你好",
  "input:你的名字是",
  "output:AI?",
  "input:我的名字是Oriana",
  "output:你好",
  "input:你的生日是",
  "output:2/30號",
  "input:你喜歡玩什麼遊戲",
  "output:我不喜歡玩遊戲",
  "input:你好爛",
  "output:抱歉",
  "input:我喜歡你",
  "output:謝謝",f'input: {prompt}'
]
  

  chat = chat_history[ca].setdefault(str(id),model.start_chat())
  response = chat.send_message(prompt_parts)
  return response.text

def calling_gemini_api(data):
    url = f'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
      print(response.json())
      return response.json()
    else:
      return "Error"

def calling_gemini_vision_api(text, image_base64_string):
    prompt_part = f"你是一個AI，你對於任何情況的回應，會盡量以最短的回應回答，個性有點單純 input: {text}"

    url = f'https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}'
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_part},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64_string
                        }
                    }
                ]
            },
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
      return response.json()
    else:
      print(response.json())
      return "Error"

app = Flask(__name__)

channel_access_token = os.environ['channel_access_token']
channel_secret = os.environ['channel_secret']

help_list = """❗指令列表❗
幫助：取得指令列表
關於：取得相關資訊

直接對話即可使用AI
目前支援：
輸入 | 文字、圖片
輸出 | 文字"""

# 這裡需要替換成你的Channel Access Token和Channel Secret
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/", methods=['GET'])
def main():
  return "Hello World!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
  user_message = event.message.text
  if user_message == "幫助":
    reply_message = help_list
  else:
    if event.source.type == "group":
      reply_message = calling_sue(user_message,"group",event.source.group_id)
      if reply_message == "Error":
        reply_message = "發生錯誤，請稍後再試"
    else:
      reply_message = calling_sue(user_message,"user",event.source.user_id)
  line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    # 獲取圖片訊息的內容
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    image_data = message_content.content
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    reply_message = calling_gemini_vision_api("用繁體中文描述這張圖片", image_base64)

    if reply_message == "Error":
        reply_message = "發生錯誤，請稍後再試"
    else:
      print(reply_message)
      reply_message = reply_message["candidates"][0]["content"]["parts"][0]["text"]

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000)