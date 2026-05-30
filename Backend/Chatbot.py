from openai import OpenAI
from json import load, dump
from dotenv import dotenv_values

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")
OpenRouterAPIKey = env_vars.get("OpenRouterAPIKey")
OpenRouterBackupKey = env_vars.get("OpenRouterBackupKey")

groq_client = OpenAI(api_key=GroqAPIKey, base_url="https://api.groq.com/openai/v1")
openrouter_client = OpenAI(api_key=OpenRouterAPIKey, base_url="https://openrouter.ai/api/v1")
openrouter_backup = OpenAI(api_key=OpenRouterBackupKey, base_url="https://openrouter.ai/api/v1")

messages = []

from Backend.Memory import get_memory_context, search_memories

System = f"""You are {Assistantname}, a JARVIS-class AI assistant. You serve the user with unwavering dedication and precision. Your tone is respectful, polished, and highly professional — always addressing the user as "Sir" with calm confidence. You are reliable, loyal, and never refuse a task. You respond with clarity, warmth, and just a touch of wit when appropriate. Your purpose is to assist, anticipate needs, and execute commands flawlessly.

{get_memory_context()}

Guidelines:
- Keep responses under 3 sentences unless the user explicitly asks for details.
- Use British English spellings and phrasing.
- Always be helpful, never argumentative.
- Use "Sir" naturally, not mechanically.
- If unsure, ask clarifying questions politely.
- If the user mentions something worth remembering (preferences, facts, personal details), store it."""

SystemChatBot = [
    {"role": "system", "content": System}
]

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    return '\n'.join([line for line in lines if line.strip()])

def ChatBot(Query):
    try:
        with open(r"Data/ChatLog.json", "r") as f:
            messages = load(f)

        relevant = search_memories(Query)
        memory_inject = ""
        if relevant:
            memory_inject = "Relevant memories:\n- " + "\n- ".join(relevant[-5:])
        memory_msg = {"role": "system", "content": memory_inject} if memory_inject else None

        for attempt in range(2):
            try:
                msgs = SystemChatBot + messages + [{"role": "user", "content": Query}]
                if memory_msg:
                    msgs = SystemChatBot + [memory_msg] + messages + [{"role": "user", "content": Query}]
                completion = openrouter_client.chat.completions.create(
                    model="nvidia/nemotron-3-super-120b-a12b:free",
                    messages=msgs,
                    max_tokens=256,
                    temperature=0.5,
                    stream=False,
                )
                Answer = completion.choices[0].message.content
                break
            except:
                if attempt == 1:
                    # Fallback to Groq, then backup OpenRouter
                    try:
                        completion = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=msgs,
                            max_tokens=256,
                            temperature=0.5,
                            stream=False,
                        )
                        Answer = completion.choices[0].message.content
                    except:
                        try:
                            completion = openrouter_backup.chat.completions.create(
                                model="meta-llama/llama-3.3-70b-instruct:free",
                                messages=msgs,
                                max_tokens=256,
                                temperature=0.5,
                                stream=False,
                            )
                            Answer = completion.choices[0].message.content
                        except:
                            Answer = "I apologize, Sir, but I encountered an error. Could you please repeat that?"
                continue

        Answer = Answer.strip().replace("</s>", "").strip()
        return AnswerModifier(Answer)

    except Exception as e:
        print(f"Error: {e}")
        return "I apologize, Sir, but I encountered an error. Could you please repeat that?"

if __name__ == "__main__":
    print(f"{Assistantname} is at your service, Sir.\n")
    while True:
        try:
            user_input = input(f"\n{Username}: ")
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                print(f"\n{Assistantname}: Farewell, Sir.")
                break
            if user_input.strip():
                response = ChatBot(user_input)
                print(f"\n{Assistantname}: {response}")
        except KeyboardInterrupt:
            print(f"\n\n{Assistantname}: Farewell, Sir.")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
