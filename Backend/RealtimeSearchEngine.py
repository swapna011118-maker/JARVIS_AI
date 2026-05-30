from openai import OpenAI
from json import load, dump
from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
import re

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

def _get_system_prompt():
    from Backend.Memory import get_memory_context
    env = dotenv_values(".env")
    loc = env.get("UserLocation", "")
    mem = get_memory_context()
    mem_section = f"\n{mem}\n" if mem else ""
    return f"""You are {Assistantname}, a JARVIS-class AI assistant. You serve the user with unwavering dedication and precision. Your tone is respectful, polished, and highly professional — always addressing the user as "Sir" with calm confidence. You are reliable, loyal, and never refuse a task. You respond with clarity, warmth, and just a touch of wit when appropriate. Your purpose is to assist, anticipate needs, and execute commands flawlessly.

User's location: {loc}
{mem_section}
Guidelines:
- Speak concisely and clearly unless asked to elaborate.
- Use British English spellings and phrasing.
- Always be helpful, never argumentative.
- Use "Sir" naturally, not mechanically.
- When given search results, answer using the most relevant information from them. If the results contain the answer, provide it clearly. Keep responses concise — 2-3 sentences max unless more detail is requested."""

SystemChatBot = [
    {"role": "system", "content": _get_system_prompt()}
]

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    return '\n'.join([line for line in lines if line.strip()])

def web_search(query):
    from ddgs import DDGS
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=6))
        if not results:
            return ""
        lines = []
        for r in results:
            title = r.get('title', '').strip()
            snippet = r.get('body', r.get('snippet', '')).strip()
            if title and snippet:
                lines.append(f"{title}: {snippet}")
        return '\n'.join(lines)
    except:
        try:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for res in soup.select(".result__body"):
                title = res.select_one(".result__title")
                snippet = res.select_one(".result__snippet")
                if title and snippet:
                    results.append(f"{title.get_text(strip=True)}: {snippet.get_text(strip=True)}")
            return '\n'.join(results[:6])
        except:
            pass
    return ""

def RealtimeSearchEngine(Query):
    try:
        with open(r"Data/ChatLog.json", "r") as f:
            messages = load(f)

        search_results = web_search(Query)
        is_near_me = 'near me' in Query.lower()

        if is_near_me and search_results:
            lines = search_results.split('\n')
            places = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('- '):
                    line = line[2:]
                if ':' in line:
                    title = line.split(':', 1)[0].strip()
                else:
                    title = line[:80].strip()
                if title and title not in places:
                    places.append(title)

            env = dotenv_values(".env")
            loc = env.get("UserLocation", "")
            if places:
                formatted = '\n'.join(f'- {p}' for p in places[:12])
                Answer = f"Sir, here are some places near {loc}:\n{formatted}\n\nWould you like directions to any of these?"
            else:
                Answer = f"I found some listings near {loc}:\n{search_results[:500]}\n\nWould you like directions?"
            return AnswerModifier(Answer)

        from Backend.Memory import search_memories
        relevant = search_memories(Query)
        memory_inject = ""
        if relevant:
            memory_inject = "Relevant memories:\n- " + "\n- ".join(relevant[-5:])

        context = SystemChatBot.copy()
        if memory_inject:
            context.append({"role": "system", "content": memory_inject})

        if search_results:
            lines = search_results.split('\n')
            formatted = '\n'.join(f'- {l}' for l in lines if l.strip())
            user_content = f"Search results for \"{Query}\":\n{formatted}\n\nAnswer the user: {Query}"
        else:
            user_content = Query

        user_entry = {"role": "user", "content": user_content}

        for attempt in range(2):
            try:
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=context + messages + [user_entry],
                    max_tokens=256,
                    temperature=0.3,
                    stream=False,
                )
                Answer = completion.choices[0].message.content
                break
            except:
                if attempt == 1:
                    try:
                        completion = openrouter_client.chat.completions.create(
                            model="google/gemini-2.0-flash-001",
                            messages=context + messages + [user_entry],
                            max_tokens=256,
                            temperature=0.3,
                            stream=False,
                        )
                        Answer = completion.choices[0].message.content
                    except:
                        try:
                            completion = openrouter_backup.chat.completions.create(
                                model="google/gemini-2.0-flash-001",
                                messages=context + messages + [user_entry],
                                max_tokens=256,
                                temperature=0.3,
                                stream=False,
                            )
                            Answer = completion.choices[0].message.content
                        except:
                            Answer = "I couldn't find updated information on that, Sir. Could you try asking differently?"
                continue

        Answer = Answer.strip().replace("</s>", "").strip()
        return AnswerModifier(Answer)

    except Exception as e:
        print(f"Error: {e}")
        return "I apologize, Sir, but I encountered an error."

if __name__ == "__main__":
    print(f"{Assistantname} is at your service, Sir.\n")
    while True:
        try:
            user_input = input(f"\n{Username}: ")
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                print(f"\n{Assistantname}: Farewell, Sir.")
                break
            if user_input.strip():
                response = RealtimeSearchEngine(user_input)
                print(f"\n{Assistantname}: {response}")
        except KeyboardInterrupt:
            print(f"\n\n{Assistantname}: Farewell, Sir.")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
