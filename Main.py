from Frontend.GUI import (
	GraphicalUserInterface,
	SetAssistantStatus,
	ShowTextToScreen,
	TempDirectoryPath,
	SetMicrophoneStatus,
	AnswerModifier,
	GetMicrophoneStatus,
	GetAssistantStatus,
)

from dotenv import dotenv_values
from time import sleep
import threading
import json

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f''' Welcome {Username}. I am doing well. How may I help you?'''

def ShowDefaultChatIfNoChats():
	File = open(r'Data/ChatLog.json', "r", encoding='utf-8')
	if len(File.read()) < 5:
		with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
			file.write("")
		with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
			file.write(DefaultMessage)

def InitialExecution():
	SetMicrophoneStatus("False")
	ShowTextToScreen("")
	try:
		with open(r'Data/ChatLog.json', 'w') as f:
			json.dump([], f)
	except:
		pass
	ShowDefaultChatIfNoChats()

InitialExecution()

def SecondThread():
	GraphicalUserInterface()

if __name__ == "__main__":
	SecondThread()
