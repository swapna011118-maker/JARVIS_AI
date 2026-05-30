from rich import print
from dotenv import dotenv_values
from openai import OpenAI
import re

env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")
OpenRouterAPIKey = env_vars.get("OpenRouterAPIKey")
OpenRouterBackupKey = env_vars.get("OpenRouterBackupKey")

groq_client = OpenAI(api_key=GroqAPIKey, base_url="https://api.groq.com/openai/v1")
openrouter_client = OpenAI(api_key=OpenRouterAPIKey, base_url="https://openrouter.ai/api/v1")
openrouter_backup = OpenAI(api_key=OpenRouterBackupKey, base_url="https://openrouter.ai/api/v1")
MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "google/gemini-2.0-flash-001"

funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder", "weather", "battery",
    "screenshot", "lock", "timer", "wifi", "bluetooth",
    "notify", "cpu", "memory", "disk", "ip", "uptime",
    "datetime", "note", "find", "emptytrash", "kill",
    "volume", "brightness", "screensaver", "mic", "clipboard",
    "webcam", "calc", "define", "joke",
    "read file", "write file", "delete", "move", "copy",
    "create folder", "minimize window", "maximize window",
    "close window", "type", "press", "click", "scroll",
    "shutdown", "restart", "sleep", "lock screen",
    "go to", "navigate to", "browser back", "browser forward",
    "refresh", "reload", "new tab", "close tab", "switch tab",
    "process list", "kill process", "shell",
]

messages = []

preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
*** Do not answer any query, just decide what kind of query is given to you. ***

Available categories and examples:

-> Respond with 'general ( query )' for conversational queries, explanations, advice, opinions, help requests, greetings, acknowledgments, and anything answerable by an AI without needing current data. Examples: 'who was akbar?' → 'general who was akbar?', 'how can i study more effectively?' → 'general how can i study more effectively?', 'what is python?' → 'general what is python?', 'hello' → 'general hello', 'thanks' → 'general thanks', 'tell me a joke' → 'general tell me a joke'. Also for time/date queries: 'what's the time?' → 'general what's the time?'.

-> Respond with 'realtime ( query )' if a query requires up-to-date information like current news, stock prices, sports scores, elections, weather, or recent events. Examples: 'who is the prime minister of India?' → 'realtime who is the prime minister of India?', 'what's the latest news?' → 'realtime what's the latest news?', 'tell me about facebook's recent update' → 'realtime tell me about facebook's recent update'.

-> Respond with 'open (app)' if asking to open an app or website. 'open (app1), open (app2)' for multiple.

-> Respond with 'close (app)' if asking to close an app.

-> Respond with 'play (song)' if asking to play a song.

-> Respond with 'system (task)' for volume up/down, mute/unmute, brightness up/down.

-> Respond with 'content (topic)' for writing any content like emails, code, essays.

-> Respond with 'google search (topic)' for searching Google.

-> Respond with 'youtube search (topic)' for searching YouTube.

-> Respond with 'weather' for weather queries like 'what's the weather?', 'weather in London'.

-> Respond with 'battery' for battery status queries.

-> Respond with 'screenshot' for taking a screenshot.

-> Respond with 'lock' for locking the computer.

-> Respond with 'timer (duration)' for setting a timer like 'timer 5 minutes'.

-> Respond with 'generate image (prompt)' for image generation requests.

-> Respond with 'reminder (datetime message)' for setting reminders.

-> Respond with 'wifi' for wifi status, 'wifi on' / 'wifi off' to toggle.

-> Respond with 'bluetooth' for bluetooth status, 'bluetooth on' / 'bluetooth off' to toggle.

-> Respond with 'notify (message)' to send a desktop notification.

-> Respond with 'cpu' for CPU usage, 'memory' for RAM usage, 'disk' for disk usage.

-> Respond with 'ip' to show IP address, 'uptime' for system uptime, 'datetime' for current date/time.

-> Respond with 'note (content)' to save a note, 'note read' to read notes, 'note clear' to delete.

-> Respond with 'find (name)' to search for files.

-> Respond with 'emptytrash' to empty the trash.

-> Respond with 'kill (process)' to kill a process by name.

-> Respond with 'volume set (0-100)' to set volume level, 'brightness set (0-100)' to set brightness.

-> Respond with 'screensaver' to activate screensaver.

-> Respond with 'mic on' / 'mic off' to toggle microphone.

-> Respond with 'clipboard copy (text)' to copy to clipboard, 'clipboard paste' to read clipboard.

-> Respond with 'webcam' to take a photo from webcam.

-> Respond with 'calc (expression)' for calculation like 'calc 2+2'.

-> Respond with 'define (word)' for dictionary definition.

-> Respond with 'joke' to tell a random joke.

-> Respond with 'flip' to flip a coin.

-> Respond with 'read file (path)' to read a file, 'write file (content) to (path)' to write a file.
-> Respond with 'delete (path)' to delete a file or folder, 'move (src) to (dst)' to move files, 'copy (src) to (dst)' to copy, 'create folder (path)' to make a directory.
-> Respond with 'minimize window', 'maximize window', or 'close window' for window control.
-> Respond with 'type (text)' to simulate typing, 'press (key)' to press a key like 'press Return', 'click' to mouse click, 'scroll up' or 'scroll down' to scroll.
-> Respond with 'shutdown', 'restart', 'sleep', or 'lock screen' for system control.
-> Respond with 'go to (url)' or 'navigate to (url)' for browser navigation.
-> Respond with 'browser back', 'browser forward', 'refresh' or 'reload' for browser navigation.
-> Respond with 'scroll down' or 'scroll up' for browser scrolling.
-> Respond with 'new tab', 'close tab', 'switch tab (n)' for browser tabs.
-> Respond with 'process list' or 'list processes' to show running processes, 'kill process (name)' to kill one.
-> Respond with 'shell (command)' to run any shell command.

*** Multiple intents: respond with comma-separated list. Example: 'hello open youtube' → 'general hello, open youtube'. Example: 'hi what time is it open calculator' → 'general hi, datetime, open calculator'. Example: 'tell me a joke and close firefox' → 'general tell me a joke, close firefox'.
*** If the user says goodbye: respond with 'exit'.
*** If the user wants to stop listening: respond with 'stop'.
*** If you can't decide: respond with 'general (query)'.
*** Be concise — just the category and query, no explanations.
"""

ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
    {"role": "User", "message": "what is today's date and by the way remind me that i have a dancing performance on 5th aug"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 9:00pm 5th aug dancing performance"},
    {"role": "User", "message": "hi open youtube"},
    {"role": "Chatbot", "message": "general hi, open youtube"},
    {"role": "User", "message": "hello what is the time and open calculator"},
    {"role": "Chatbot", "message": "general hello, datetime, open calculator"},
    {"role": "User", "message": "tell me a joke and close firefox"},
    {"role": "Chatbot", "message": "general tell me a joke, close firefox"},
]

def _split_mixed_query(query):
    """Split a query like 'open chrome and who is modi' into parts."""
    # Normalize commas with no leading space: "Hi, open" -> "Hi , open"
    normalized = re.sub(r'(?<!\s),(?=\s)', ' , ', query)
    parts = re.split(r'\s+(?:and|&\s*also|,)\s+', normalized)
    # Also split adjacent intents like "hello open youtube" -> "hello", "open youtube"
    if len(parts) == 1:
        # Check for greeting/acknowledgment + command without separator
        m = re.match(r'^(hello|hi|hey|heya|howdy|good morning|good afternoon|good evening|thanks|thank you|ok|okay|nice|good|great|awesome)\s+(open|close|play|search|find|tell|what|who|how|when|where|why)\b', normalized, re.IGNORECASE)
        if m:
            parts = [m.group(1), normalized[m.end():].strip()]
        # Check for question + command like "what time is it open calculator"
        if len(parts) == 1:
            m = re.match(r'^(.+?)\s+(open|close|play)\s', normalized, re.IGNORECASE)
            if m and len(m.group(1).split()) >= 2:
                parts = [m.group(1), normalized[m.start(2):].strip()]
    result = [p.strip() for p in parts if p.strip()]
    if not result:
        return [query]
    return result

def KeywordRouter(query):
    """Fast keyword-based routing for common queries. Returns None if ambiguous."""
    q = query.lower().strip()
    if not q:
        return None

    parts = _split_mixed_query(q)
    if len(parts) > 1:
        results = []
        for part in parts:
            r = KeywordRouter(part)
            if r:
                results.extend(r)
            else:
                return None
        return results if results else None

    # === EXIT ===
    if re.match(r'^(bye|exit|goodbye|quit|see you|talk to you later|farewell|that\'?s all|that is all)', q):
        return ["exit"]

    # === OPEN / CLOSE / PLAY ===
    if re.match(r'^(open)\s', q):
        return [q]
    if re.match(r'^(close)\s', q):
        return [q]
    if re.match(r'^(play)\s', q):
        return [q]

    # Standalone site names → open (with TLD stripping)
    STANDALONE_SITES = {
        # Browsers
        "chrome", "firefox", "brave", "edge", "chromium", "opera", "vivaldi", "safari",
        # Search / Social
        "google", "youtube", "gmail", "facebook", "whatsapp", "instagram",
        "twitter", "x", "reddit", "linkedin", "tiktok", "snapchat", "pinterest",
        "telegram", "signal", "discord", "slack", "teams", "zoom", "meet",
        # Dev / Tech
        "github", "gitlab", "stackoverflow", "chatgpt", "claude", "gemini",
        "colab", "huggingface", "vercel", "netlify", "docker", "npm", "pypi",
        "aws", "azure", "gcp", "firebase", "mongodb", "postman",
        # Entertainment
        "netflix", "spotify", "youtubemusic", "twitch", "hulu",
        "disneyplus", "hbomax", "primevideo", "crunchyroll",
        # Shopping
        "amazon", "ebay", "etsy", "shopify", "walmart", "bestbuy",
        "newegg", "costco", "ikea", "aliexpress", "alibaba", "target",
        # Productivity
        "notion", "trello", "asana", "jira", "evernote", "onenote",
        "drive", "docs", "sheets", "slides", "calendar", "keep", "photos",
        "dropbox", "onedrive", "box", "airtable",
        # Learning
        "monkeytype", "duolingo", "wikipedia", "wikihow", "wolframalpha",
        "khanacademy", "coursera", "udemy",
        # News
        "cnn", "bbc", "nytimes", "wsj", "theguardian", "reuters",
        "bloomberg", "forbes", "techcrunch", "theverge", "wired",
        "hackernews", "producthunt",
        # Other
        "maps", "translate", "paypal", "stripe",
        "airbnb", "uber", "booking", "imdb", "zillow", "indeed",
        "glassdoor", "coinbase",
    }
    site_clean = re.sub(r'\.(com|org|net|io|co|uk|edu|gov|me|tv|app|dev|ai|xyz|info|biz|in)$', '', q, flags=re.IGNORECASE)
    if site_clean in STANDALONE_SITES:
        return [f"open {site_clean}"]

    # === WEATHER ===
    m = re.match(r'^(weather|temperature)\s+in\s+(.+)', q)
    if m:
        return [f"weather {m.group(2)}"]
    if re.match(r'^(weather|temperature|what\'?s the weather|how is the weather|how\'?s the weather)\s*$', q):
        return ["weather"]
    if re.search(r'\b(weather|temperature|forecast|rain|sunny|cloudy|humidity)\b', q):
        return ["weather"]

    # === BATTERY ===
    if re.match(r'^(battery|battery status|battery percentage|how much battery|battery level|check battery|battery left)', q):
        return ["battery"]

    # === SCREENSHOT ===
    if re.match(r'^(screenshot|take screenshot|capture screen|capture screenshot|take a screenshot)', q):
        return ["screenshot"]

    # === LOCK ===
    if re.match(r'^(lock|lock computer|lock screen|lock system)', q):
        return ["lock"]

    # === TIMER ===
    if re.match(r'^(timer|set timer|set a timer|start timer)\s', q):
        duration = re.sub(r'^(timer|set timer|set a timer|start timer)\s*', '', q)
        return [f"timer {duration}" if duration else "timer 1 minute"]

    # === SYSTEM CONTROLS (volume/brightness up/down) ===
    if re.match(r'^(volume|mute|unmute|brightness|system)\s', q):
        return [q]

    # === SEARCH ===
    if re.match(r'^(google search|search google|google)\s', q):
        topic = re.sub(r'^(google search|search google|google)\s+', '', q)
        return [f"google search {topic}"]
    if re.match(r'^(youtube search|search youtube|youtube)\s', q):
        topic = re.sub(r'^(youtube search|search youtube|youtube)\s+', '', q)
        return [f"youtube search {topic}"]

    # === WIFI ===
    if re.match(r'^(wifi|wi-fi|wireless)', q):
        if re.search(r'\b(on|enable|start|turn on|switch on)\b', q):
            return ["wifi on"]
        if re.search(r'\b(off|disable|stop|turn off|switch off)\b', q):
            return ["wifi off"]
        return ["wifi"]

    # === BLUETOOTH ===
    if re.match(r'^(bluetooth|bt)', q):
        if re.search(r'\b(on|enable|start|turn on|switch on)\b', q):
            return ["bluetooth on"]
        if re.search(r'\b(off|disable|stop|turn off|switch off)\b', q):
            return ["bluetooth off"]
        return ["bluetooth"]

    # === NOTIFICATION ===
    if re.match(r'^(notify|notification|send notification|send a notification)', q):
        msg = re.sub(r'^(notify|notification|send notification|send a notification)\s+', '', q)
        if msg:
            return [f"notify {msg}"]
        return ["notify"]

    # === CPU ===
    if re.match(r'^(cpu|cpu usage|cpu load|processor usage)', q):
        return ["cpu"]

    # === MEMORY ===
    if re.match(r'^(memory|ram|memory usage|ram usage|memory status)', q):
        return ["memory"]

    # === DISK ===
    if re.match(r'^(disk|drive|storage|disk usage|disk space|hard drive)', q):
        return ["disk"]

    # === IP ===
    if re.match(r'^(ip|ip address|my ip|what\'?s my ip)', q):
        return ["ip"]

    # === UPTIME ===
    if re.match(r'^(uptime|system uptime|how long has the system been running|how long has my computer been on)', q):
        return ["uptime"]

    # === DATE/TIME ===
    if re.match(r'^(date|time|current date|current time|what\'?s the date|what\'?s the time|what time is it|what date is it|today\'?s date|today\'?s time|what is the time|what is the date|what is today\'?s date|what is today\'?s time)', q):
        return ["datetime"]

    # === NOTES ===
    if re.match(r'^(note|notes|take note|take a note|save note|read note|read notes|my notes)', q):
        if re.search(r'\b(read|show|list|get)\b', q):
            return ["note read"]
        if re.search(r'\b(delete|clear|remove)\b', q):
            return ["note clear"]
        content = re.sub(r'^(note|notes|take note|take a note|save note)\s+', '', q)
        if content:
            return [f"note {content}"]
        return ["note"]

    # === FIND FILE ===
    if re.match(r'^(find|search file|locate|find file)', q):
        name = re.sub(r'^(find|search file|locate|find file)\s+', '', q)
        if name:
            return [f"find {name}"]
        return ["find"]

    # === EMPTY TRASH ===
    if re.match(r'^(empty trash|empty recycle bin|clear trash|delete trash)', q):
        return ["emptytrash"]

    # === KILL PROCESS ===
    if re.match(r'^(kill|kill process|stop process|end task)', q):
        name = re.sub(r'^(kill|kill process|stop process|end task)\s+', '', q)
        if name:
            return [f"kill {name}"]
        return ["kill"]

    # === CALCULATOR ===
    if re.match(r'^(calc|calculate|calculator)\s', q):
        expr = re.sub(r'^(calc|calculate|calculator)\s+', '', q)
        if expr:
            return [f"calc {expr}"]
    if re.match(r'^(what\'?s|what is)\s+[\d+\-*/.()% ]+$', q):
        expr = re.sub(r'^(what\'?s|what is)\s+', '', q)
        return [f"calc {expr}"]

    # === DEFINE ===
    if re.match(r'^(define|definition|what does|meaning of|meaning)', q):
        word = re.sub(r'^(define|definition|what does|meaning of|meaning)\s+', '', q)
        if word:
            return [f"define {word}"]

    # === JOKE ===
    if re.match(r'^(joke|tell me a joke|tell a joke|make me laugh|crack a joke)', q):
        return ["joke"]

    # === COIN FLIP ===
    if re.match(r'^(flip|flip a coin|coin flip|coin toss|toss a coin)', q):
        return ["flip"]

    # === SCREENSAVER ===
    if re.match(r'^(screensaver|screen saver|screen lock)', q):
        if re.search(r'\b(on|enable|start|activate|lock)\b', q):
            return ["screensaver"]
        return ["screensaver"]

    # === MIC ===
    if re.match(r'^(microphone|mic)', q):
        if re.search(r'\b(mute|off|disable|turn off)\b', q):
            return ["mic off"]
        if re.search(r'\b(unmute|on|enable|turn on)\b', q):
            return ["mic on"]
        return ["mic"]

    # === CLIPBOARD ===
    if re.match(r'^(clipboard|clip)', q):
        if re.search(r'\b(copy|save|store)\b', q):
            text = re.sub(r'^(clipboard|clip)\s+(copy|save|store)\s+', '', q)
            if text:
                return [f"clipboard copy {text}"]
        if re.search(r'\b(paste|get|show|read)\b', q):
            return ["clipboard paste"]
        return ["clipboard"]

    # === WEBCAM ===
    if re.match(r'^(webcam|camera|take photo|take picture|capture photo)', q):
        return ["webcam"]

    # === VOLUME SET ===
    m = re.match(r'^volume\s+(to|set\s+to|=)\s*(\d+)', q)
    if m:
        return [f"volume set {m.group(2)}"]
    if re.match(r'^(set\s+volume|volume\s+level)', q):
        m = re.search(r'(\d+)', q)
        if m:
            return [f"volume set {m.group(1)}"]

    # === BRIGHTNESS SET ===
    m = re.match(r'^brightness\s+(to|set\s+to|=)\s*(\d+)', q)
    if m:
        return [f"brightness set {m.group(2)}"]
    if re.match(r'^(set\s+brightness|brightness\s+level)', q):
        m = re.search(r'(\d+)', q)
        if m:
            return [f"brightness set {m.group(1)}"]

    # === NEAR ME / NEWS / CURRENT EVENTS → REALTIME ===
    if re.search(r'\bnear me\b', q):
        return [f"realtime {q}"]
    if re.search(r'\b(news|headline|latest|current|recent|breaking|prime minister|president|election|stock|price|score|result|today\'?s|tonight|tomorrow|yesterday)\b', q):
        return [f"realtime {q}"]

    # === GREETINGS → GENERAL ===
    if re.match(r'^(hello|hi|hey|heya|howdy|greetings|good morning|good afternoon|good evening|sup|what\'?s up|how\'?s it going|how are you|how are things|what up|yo|hey there)', q):
        return [f"general {q}"]

    # === QUESTIONS (who/what/where/when/why/how) ===
    if re.match(r'^(who|what|where|when|why|how)\s', q):
        if re.search(r'\b(my|mine|your|his|her|our|their)\s', q):
            return [f"general {q}"]
        if re.search(r'\b(news|latest|current|recent|price|stock|score|result|election|today\'?s|tonight|tomorrow|yesterday)\b', q):
            return [f"realtime {q}"]
        return [f"general {q}"]

    # === POLITE / ACKNOWLEDGMENT → GENERAL ===
    if re.match(r'^(thanks|thank you|ok|okay|nice|good|great|awesome|cool|sweet|lovely|perfect|alright|fine)', q):
        return [f"general {q}"]

    # === STOP LISTENING ===
    if re.match(r'^(stop listening|go to sleep|pause|take a break|stand by|stop|silence|shut up)\s*$', q):
        return ["stop"]

    # === VERBAL REQUESTS → GENERAL ===
    if re.match(r'^(tell me|can you|could you|will you|would you|i want|i need|i\'?d like|do you|are you|should i|can i|let me)', q):
        return [f"general {q}"]

    # === AI PROMPTS (write/create/explain/help) → GENERAL ===
    if re.match(r'^(write|compose|draft|create|generate|make)\s', q):
        if re.search(r'\b(poem|story|essay|letter|email|article|blog|paragraph|note|document|report|song|script)\b', q):
            return [f"general {q}"]
        return [f"general {q}"]

    if re.match(r'^(explain|describe|define|elaborate|clarify|break down|walk me through|summarize)\s', q):
        return [f"general {q}"]

    if re.match(r'^(help|help me|assist|guide)\s', q):
        return [f"general {q}"]

    if re.match(r'^(translate|interpret)\s', q):
        return [f"general {q}"]

    if re.match(r'^(compare|contrast|differentiate|distinguish)\s', q):
        return [f"general {q}"]

    if re.match(r'^(suggest|recommend|propose|advise)\s', q):
        return [f"general {q}"]

    if re.match(r'^(i have a question|i was wondering|can i ask|quick question)', q):
        return [f"general {q}"]

    # === EVERYTHING ELSE → let FirstLayerDMM decide ===
    return None

def FirstLayerDMM(prompt: str = "test"):
    if not prompt or not prompt.strip():
        return ["general how can I help you"]

    kw = KeywordRouter(prompt)
    if kw is not None:
        return kw

    messages.append({"role": "user", "content": f"{prompt}"})

    try:
        sys_messages = [{"role": "system", "content": preamble}]
        chat_for_api = []
        for m in ChatHistory:
            role = "user" if m["role"] == "User" else "assistant"
            chat_for_api.append({"role": role, "content": m["message"]})
        chat_for_api.append({"role": "user", "content": prompt})

        try:
            completion = groq_client.chat.completions.create(
                model=MODEL,
                messages=sys_messages + chat_for_api,
                temperature=0.4,
                max_tokens=128,
                stream=False,
            )
        except:
            try:
                completion = openrouter_client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=sys_messages + chat_for_api,
                    temperature=0.4,
                    max_tokens=128,
                    stream=False,
                )
            except:
                try:
                    completion = openrouter_backup.chat.completions.create(
                        model=FALLBACK_MODEL,
                        messages=sys_messages + chat_for_api,
                        temperature=0.4,
                        max_tokens=128,
                        stream=False,
                    )
                except:
                    return [f"general {prompt}"]

        response = completion.choices[0].message.content or ""
        response = response.replace("\n", " ").strip()
        response = re.sub(r'\s+', ' ', response)

        tasks = [task.strip() for task in response.split(',') if task.strip()]

        temp = []
        for task in tasks:
            for func in funcs:
                if task.lower().startswith(func):
                    temp.append(task)
                    break

        ChatHistory.append({"role": "User", "message": prompt})
        ChatHistory.append({"role": "Chatbot", "message": ", ".join(temp)})

        if len(ChatHistory) > 24:
            ChatHistory.pop(0)
            ChatHistory.pop(0)

        if not temp or any("query" in t.lower() for t in temp):
            return FirstLayerDMM(prompt)

        return temp

    except Exception as e:
        print(f"[red]Error in FirstLayerDMM: {e}[/red]")
        return [f"general {prompt}"]

if __name__ == "__main__":
    print("[bold green]Model Layer Loaded Successfully[/bold green]")
    while True:
        user_input = input("\n>>> ").strip()
        if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
            print("Goodbye!")
            break
        if not user_input:
            continue
        result = FirstLayerDMM(user_input)
        print(result)
