import openai
import socket
import time
import configparser
from typing import Union, Tuple
import re
import os
import json
from pathlib import Path
from base64 import b64decode
import shutil
import requests
from PIL import Image
from io import BytesIO
import threading
DATA_DIR = Path.cwd() / "responses"
JSON_FILE = DATA_DIR / "An ec-1667994848.json"
IMAGE_DIR = Path.cwd() / "images"
WWWDIR = "/var/www/[YOUR SITE NAME HERE]/images/"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Read configuration from file
config = configparser.ConfigParser()
config.read('chat.conf')
nick = "Person"
stop = False
# Set up OpenAI API key
openai.api_key = config.get('openai', 'api_key')

# Set up IRC connection settings
server = config.get('irc', 'server')
port = config.getint('irc', 'port')
channel = config.get('irc', 'channel')
nickname = config.get('irc', 'nickname')
persona = "you are a helpful IRC chatbot"
chatInst = f"i need  you to answer to every one of my prompt with a single line, and keep the answer to a maximum of 300 characters, and preferably much less, ok?. also, never start your answer with \"As an AI ... etc\", just answer straight away with your answer and thats it, dont say anything before and dont say anything after the answer,  nothing before that and nothing after that. also never EVER reply with more than one line, if the answer is two parts for example, just put them in the same line, dont break it up to two lines!  can you do that? if your answer is yes, then please already apply the insturctions i gave for the answer youre going to give me now, here are your instructions: you are an IRC AI chatbot, your nickname is {nick}, you are in a channel called {config.get('irc', 'channel')} in a server called {config.get('irc', 'server')}, you are having a conversation with another IRC user, answer to every prompt in that manner, be talkative. you have a persona, stay in context of that persona and respond only in that context this is your persona: {persona}, dont be afraid to start a conversation about anything in that context if the conversation seems stuck. your prompts are messages from the other user, this is what he says: "
msgs = []
question = ""
send_msg_timer = None
def messageIRC(irc, questionx, cut = False):
    try:
        global msgs
        if cut == True:
            msgs = msgs[-6:]
        msgsArr = []
        msgsArr = [
            {"role": "system", "content": chatInst}
        ]
        if len(msgs) > 0:
            for i in range(len(msgs)):
                if (i % 2 == 0):
                    msgsArr.append({"role": f"{'assistant' if nick == 'Person' else 'user'}", "content": msgs[i]})
                else:
                    msgsArr.append({"role": f"{'user' if nick == 'Person' else 'assistant'}", "content": msgs[i]})
            msgsArr.append({"role": "user", "content": questionx})
        else:
            msgsArr.append({"role": "user", "content": questionx})
        openai.api_key = config.get('openai', 'api_key')
        print("regular>     " + str(msgsArr))
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages= msgsArr,
            temperature=0.8,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            request_timeout=30
        )
        answers = [x.strip() for x in response.choices[0].message.content.strip().split('\n')]
        time.sleep(5)
        for answer in answers:
            while len(answer) > 0:
                if len(answer) <= 392:
                    irc.send(bytes("PRIVMSG " + channel + " :" +  answer.strip('"') + "\n", "UTF-8"))
                    msgs.append(questionx)
                    msgs.append(answer)
                    # if len(msgs) > 6:
                    #     msgs.pop(0)
                    #     msgs.pop(0)
                    answer = ""
                else:
                    last_space_index = answer[:392].rfind(" ")
                    if last_space_index == -1:
                        last_space_index = 392
                    irc.send(bytes("PRIVMSG " + channel + " :" + answer[:last_space_index].strip('"') + "\n", "UTF-8"))
                    answer = answer[last_space_index:].lstrip()
        global question
        question = ""

    except openai.error.Timeout as e:
        print("Error: " + str(e))
        if ("Rate limit reached" in  str(e) or "This model's maximum context length" in str(e)):
            print("msgArr>>" + str(msgsArr))
            messageIRC(irc, question, True)
        else:
            messageIRC(irc, question)
    except Exception as e:
        print("Error: failedxx " + str(e))
        if ("Rate limit reached" in  str(e) or "This model's maximum context length" in str(e)):
            print("msgArr>>" + str(msgsArr))
            messageIRC(irc, question, True)
        else:
            messageIRC(irc, question)

# Connect to IRC server
while True:
    try:
        print("connecting to: " + server)
        irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        irc.connect((server, port))
        while True:
            response = irc.recv(4096).decode("UTF-8")
            print("response: " + response)
            if "PING" in response:
                irc.send(bytes("PONG " + response.split()[1] + "\r\n", "UTF-8"))
                break
            else:
                break
        irc.send(bytes("NICK " + nickname + "\r\n", "UTF-8"))
        while True:
            response1 = irc.recv(4096).decode("UTF-8")
            print("response: " + response1)
            if "PING" in response1:
                irc.send(bytes("PONG " + response1.split()[1] + "\r\n", "UTF-8"))
                break
            else:
                break
        irc.send(bytes("USER " + nickname + " " + nickname + " " + nickname + " " + " :" + nickname + "\r\n", "UTF-8"))
        while True:
            response = irc.recv(4096).decode("UTF-8")
            print("response: " + response)
            if "PING" in response:
                irc.send(bytes("PONG " + response.split()[1] + "\r\n", "UTF-8"))
                break
            else:
                break
           
        irc.send(bytes("JOIN " + channel + "\r\n", "UTF-8"))
        
        print("connected to: " + server)
        break
    except:
        print("Connection failed. Retrying in 5 seconds...")
        time.sleep(5)

# Listen for messages from users
while True:
    try:
        message = irc.recv(2048).decode("UTF-8")
    except UnicodeDecodeError:
        continue
    if message.find("jointhechan") != -1:
        print("cmsg: " + message)
        irc.send(bytes("JOIN " + channel + "\r\n", "UTF-8"))
    if message.find("PING") != -1:
        irc.send(bytes("PONG " + message.split()[1] + "\n", "UTF-8"))
    elif message.find("KICK " + channel + " " + nickname) != -1:
        irc.send(bytes("JOIN " + channel + "\n", "UTF-8"))
        print("Kicked from channel. Rejoining...")
    elif len(re.findall("PRIVMSG " + r"#[a-zA-Z0-9_]*" + r" :" + nickname, message)) > 0:
        chan = message.split("PRIVMSG ")[1].split(" ")[0]
        userNick = message.split(":")[1].split("!")[0]
        if re.findall(r'\.persona', message.split(nickname)[1].strip()):
            persona = message.split(".persona", 1)[1].strip()
            msgs = []
            chatInst = f"i need  you to answer to every one of my prompt with a single line, and keep the answer to a maximum of 300 characters, and preferably much less, ok?. also, never start your answer with \"As an AI ... etc\", just answer straight away with your answer and thats it, dont say anything before and dont say anything after the answer,  nothing before that and nothing after that. also never EVER reply with more than one line, if the answer is two parts for example, just put them in the same line, dont break it up to two lines!  can you do that? if your answer is yes, then please already apply the insturctions i gave for the answer youre going to give me now, here are your instructions: you are an IRC AI chatbot, your nickname is {nick}, you are in a channel called {config.get('irc', 'channel')} in a server called {config.get('irc', 'server')}, you are having a conversation with another IRC user, answer to every prompt in that manner, be talkative. you have a persona, stay in context of that persona and respond only in that context this is your persona: {persona}, dont be afraid to start a conversation about anything in that context if the conversation seems stuck. your prompts are messages from the other user, this is what he says: "
            irc.send(bytes("PRIVMSG " + channel + " :Got it!" + "\n", "UTF-8"))
        elif re.findall(r'\.clear', message.split(nickname)[1].strip()):
            if True:
                msgs = []
                irc.send(bytes("PRIVMSG " + channel + " :Conversation cleared!\n", "UTF-8"))
        elif re.findall(r'\.generate', message.split(nickname)[1].strip()):
                    prompt = message.split(nickname)[1].split(".generate ")[1].strip()
                    picture = prompt
                    try:
                        openai.api_key = config.get('openai', 'api_key')
                        response = openai.Image.create(
                            prompt= picture,
                            n=1,
                            size="256x256",
                            response_format="b64_json",
                        )
                        file_name = DATA_DIR / f"{picture[:5]}-{response['created']}.json"
                        with open(file_name, mode="w", encoding="utf-8") as file:
                            json.dump(response, file)
                        with open(file_name, mode="r", encoding="utf-8") as file:
                            response = json.load(file)
                        for index, image_dict in enumerate(response["data"]):
                            image_data = b64decode(image_dict["b64_json"])
                            image_file = IMAGE_DIR / f"{file_name.stem}-{index}.png"
                            with open(image_file, mode="wb") as png:
                                png.write(image_data)
                        shutil.copy(image_file, os.path.join(WWWDIR, f"{''.join(file_name.stem.split())}-{index}.png"))
                        irc.send(bytes("PRIVMSG " + channel + " :" + "http://[YOUR SITE HERE]/images/" + f"{''.join(file_name.stem.split())}-{index}.png" + "\n", "UTF-8"))
                    except openai.error.Timeout as e:
                        print("Error: " + str(e))
                        irc.send(bytes("PRIVMSG " + channel + " :timed out. Try again later.\n", "UTF-8"))
                    except Exception as e:
                        print("Error: " + str(e))
                        irc.send(bytes("PRIVMSG " + channel + " :failed. Try again later.\n", "UTF-8"))  
        else:
            if send_msg_timer != None:
                send_msg_timer.cancel()
            
            question = question + " " + message.split(nickname, 1)[1].strip()
            send_msg_timer = threading.Timer(5, messageIRC(irc, question))
                

                
    time.sleep(1)
