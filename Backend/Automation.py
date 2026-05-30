import os
import subprocess
import asyncio
import requests
import time
import re
import shutil
import threading
import difflib
from dotenv import load_dotenv
from groq import Groq
from rich import print
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from Backend.TextToSpeech import TextToSpeech

# =====================================================================
# LOAD ENV
# =====================================================================

load_dotenv(".env")

GroqAPIKey = os.getenv("GroqAPIKey")
Assistantname = os.getenv("Assistantname", "Jarvis")

client = Groq(api_key=GroqAPIKey)

# Path for writing responses to chat screen
_AUTO_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESPONSES_FILE = os.path.join(_AUTO_BASE, "Frontend", "Files", "Responses.data")

def _write_jarvis_response(text):
    with open(_RESPONSES_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n{Assistantname}: {text}")

messages = []

SystemChatBot = [
    {
        "role": "system",
        "content": f"Hello, I am {os.environ.get('USER', 'User')}, You're a content writer."
    }
]

# =====================================================================
# GLOBALS
# =====================================================================

URL_DEBOUNCE_CACHE = {}

useragent = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# =====================================================================
# FAST BROWSER DETECTION
# =====================================================================

def get_best_browser():

    browsers = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
        "firefox"
    ]

    for browser in browsers:
        if shutil.which(browser):
            return browser

    return "xdg-open"

BROWSER = get_best_browser()

# =====================================================================
# FUZZY APP MATCHING
# =====================================================================

_AVAILABLE_BINS = None
_BIN_LOCK = threading.Lock()

def _refresh_binaries():
    global _AVAILABLE_BINS
    bins = set()
    for path_dir in os.environ.get("PATH", "").split(":"):
        if os.path.isdir(path_dir):
            try:
                for entry in os.listdir(path_dir):
                    fp = os.path.join(path_dir, entry)
                    if os.path.isfile(fp) and os.access(fp, os.X_OK):
                        bins.add(entry.lower())
            except PermissionError:
                pass
    _AVAILABLE_BINS = sorted(bins)

def _get_available_binaries():
    global _AVAILABLE_BINS
    if _AVAILABLE_BINS is None:
        with _BIN_LOCK:
            if _AVAILABLE_BINS is None:
                _refresh_binaries()
    return _AVAILABLE_BINS

def _fuzzy_match_bin(name):
    name = name.lower().strip()
    bins = _get_available_binaries()
    matches = difflib.get_close_matches(name, bins, n=5, cutoff=0.5)
    if matches:
        return matches[0]
    words = name.replace("-", " ").replace("_", " ").split()
    for candidate in bins:
        if all(w in candidate for w in words):
            return candidate
    for candidate in bins:
        if any(w == candidate for w in words):
            return candidate
    return None

# =====================================================================
# FAST WEBSITE MAP
# =====================================================================

FAST_WEB_MAP = {
    # Google services
    "google":       "https://www.google.com",
    "gmail":        "https://mail.google.com",
    "drive":        "https://drive.google.com",
    "docs":         "https://docs.google.com",
    "sheets":       "https://sheets.google.com",
    "slides":       "https://slides.google.com",
    "calendar":     "https://calendar.google.com",
    "keep":         "https://keep.google.com",
    "photos":       "https://photos.google.com",
    "translate":    "https://translate.google.com",
    "maps":         "https://maps.google.com",
    "meet":         "https://meet.google.com",
    "colab":        "https://colab.research.google.com",
    "gemini":       "https://gemini.google.com",
    "firebase":     "https://firebase.google.com",
    # Social
    "youtube":      "https://www.youtube.com",
    "youtubemusic": "https://music.youtube.com",
    "facebook":     "https://www.facebook.com",
    "instagram":    "https://www.instagram.com",
    "twitter":      "https://x.com",
    "x":            "https://x.com",
    "reddit":       "https://www.reddit.com",
    "whatsapp":     "https://web.whatsapp.com",
    "discord":      "https://discord.com",
    "slack":        "https://slack.com",
    "telegram":     "https://web.telegram.org",
    "signal":       "https://signal.org",
    "snapchat":     "https://www.snapchat.com",
    "pinterest":    "https://www.pinterest.com",
    "tiktok":       "https://www.tiktok.com",
    "linkedin":     "https://www.linkedin.com",
    # Dev / Tech
    "github":          "https://github.com",
    "gitlab":          "https://gitlab.com",
    "stackoverflow":   "https://stackoverflow.com",
    "chatgpt":         "https://chatgpt.com",
    "claude":          "https://claude.ai",
    "huggingface":     "https://huggingface.co",
    "npm":             "https://www.npmjs.com",
    "pypi":            "https://pypi.org",
    "docker":          "https://hub.docker.com",
    "vercel":          "https://vercel.com",
    "netlify":         "https://netlify.com",
    "aws":             "https://aws.amazon.com",
    "azure":           "https://azure.microsoft.com",
    "mongodb":         "https://www.mongodb.com",
    "postman":         "https://www.postman.com",
    # Entertainment
    "netflix":      "https://www.netflix.com",
    "spotify":      "https://open.spotify.com",
    "twitch":       "https://www.twitch.tv",
    "hulu":         "https://www.hulu.com",
    "disneyplus":   "https://www.disneyplus.com",
    "hbomax":       "https://www.max.com",
    "primevideo":   "https://www.primevideo.com",
    "crunchyroll":  "https://www.crunchyroll.com",
    # Shopping
    "amazon":       "https://www.amazon.com",
    "ebay":         "https://www.ebay.com",
    "etsy":         "https://www.etsy.com",
    "shopify":      "https://www.shopify.com",
    "walmart":      "https://www.walmart.com",
    "bestbuy":      "https://www.bestbuy.com",
    "newegg":       "https://www.newegg.com",
    "costco":       "https://www.costco.com",
    "ikea":         "https://www.ikea.com",
    "aliexpress":   "https://www.aliexpress.com",
    "alibaba":      "https://www.alibaba.com",
    "target":       "https://www.target.com",
    # Productivity
    "notion":       "https://www.notion.so",
    "trello":       "https://trello.com",
    "asana":        "https://app.asana.com",
    "jira":         "https://www.atlassian.com/software/jira",
    "evernote":     "https://evernote.com",
    "onenote":      "https://www.onenote.com",
    "dropbox":      "https://www.dropbox.com",
    "onedrive":     "https://onedrive.live.com",
    "box":          "https://www.box.com",
    "airtable":     "https://airtable.com",
    # Learning
    "monkeytype":   "https://monkeytype.com",
    "duolingo":     "https://www.duolingo.com",
    "wikipedia":    "https://en.wikipedia.org",
    "wikihow":      "https://www.wikihow.com",
    "wolframalpha": "https://www.wolframalpha.com",
    "khanacademy":  "https://www.khanacademy.org",
    "coursera":     "https://www.coursera.org",
    "udemy":        "https://www.udemy.com",
    # News
    "cnn":          "https://www.cnn.com",
    "bbc":          "https://www.bbc.com",
    "nytimes":      "https://www.nytimes.com",
    "wsj":          "https://www.wsj.com",
    "theguardian":  "https://www.theguardian.com",
    "reuters":      "https://www.reuters.com",
    "bloomberg":    "https://www.bloomberg.com",
    "forbes":       "https://www.forbes.com",
    "techcrunch":   "https://techcrunch.com",
    "theverge":     "https://www.theverge.com",
    "wired":        "https://www.wired.com",
    "hackernews":   "https://news.ycombinator.com",
    "producthunt":  "https://www.producthunt.com",
    # Other
    "paypal":       "https://www.paypal.com",
    "stripe":       "https://stripe.com",
    "airbnb":       "https://www.airbnb.com",
    "uber":         "https://www.uber.com",
    "booking":      "https://www.booking.com",
    "imdb":         "https://www.imdb.com",
    "zillow":       "https://www.zillow.com",
    "indeed":       "https://www.indeed.com",
    "glassdoor":    "https://www.glassdoor.com",
    "coinbase":     "https://www.coinbase.com",
}

# =====================================================================
# INSTANT URL OPENER
# =====================================================================

def open_url(url):

    current_time = time.time()

    # Prevent double opens
    if url in URL_DEBOUNCE_CACHE:

        if current_time - URL_DEBOUNCE_CACHE[url] < 1:
            return

    URL_DEBOUNCE_CACHE[url] = current_time

    try:

        subprocess.Popen(
            [BROWSER, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    except Exception:
        pass

# =====================================================================
# GOOGLE SEARCH
# =====================================================================

def GoogleSearch(topic):

    query = topic.replace(" ", "+")

    open_url(f"https://www.google.com/search?q={query}")

    text = f"Searched Google for {topic}"
    _write_jarvis_response(text)

    return True

# =====================================================================
# YOUTUBE SEARCH
# =====================================================================

def YoutubeSearch(query):

    query = query.replace(" ", "+")

    open_url(f"https://www.youtube.com/results?search_query={query}")

    text = f"Searched YouTube for {query}"
    _write_jarvis_response(text)

    return True

# =====================================================================
# ULTRA FAST YOUTUBE PLAY
# =====================================================================

def PlayYoutube(query):

    formatted_query = query.replace(" ", "+")

    search_url = (
        f"https://www.youtube.com/results?search_query={formatted_query}"
    )

    try:

        response = requests.get(
            search_url,
            headers={"User-Agent": useragent},
            timeout=5
        )

        video_ids = re.findall(
            r"watch\?v=([a-zA-Z0-9_-]{11})",
            response.text
        )

        if video_ids:

            open_url(
                f"https://www.youtube.com/watch?v={video_ids[0]}"
            )

            text = f"Playing {query}"
            _write_jarvis_response(text)
        
            return True

    except:
        pass

    open_url(search_url)

    text = f"Playing {query}"
    _write_jarvis_response(text)

    return True

# =====================================================================
# OPEN APP / WEBSITE
# =====================================================================

def OpenApp(app, sess=requests.Session()):

    app = app.lower().strip()

    # ==========================================================
    # DIRECT APP MAPPING
    # ==========================================================

    app_aliases = {

        # Browsers
        "chrome": "google-chrome",
        "google chrome": "google-chrome",
        "chromium": "chromium",
        "firefox": "firefox",
        "brave": "brave-browser",
        "edge": "microsoft-edge",

        # Linux apps
        "terminal": "ptyxis",
        "files": "nautilus",
        "file manager": "nautilus",
        "calculator": "gnome-calculator",
        "settings": "gnome-control-center",
        "text editor": "gedit",
        "vscode": "code",
        "discord": "discord",
        "spotify": "spotify",
        "steam": "steam",
    }

    # ==========================================================
    # WEBSITE FAST OPEN
    # ==========================================================

    if app in FAST_WEB_MAP:

        open_url(FAST_WEB_MAP[app])

        text = f"Opening {app}"
        _write_jarvis_response(text)
        return True

    # ==========================================================
    # WEBSITE DETECTION
    # ==========================================================

    if any(app.endswith(tld) for tld in [
        ".com",
        ".org",
        ".net",
        ".in",
        ".io"
    ]):

        url = app if app.startswith("http") else f"https://{app}"

        open_url(url)

        text = f"Opening {app}"
        _write_jarvis_response(text)
        return True

    # ==========================================================
    # APP ALIAS
    # ==========================================================

    if app in app_aliases:

        binary = app_aliases[app]

        # Launch browser app directly
        browsers = ["google-chrome", "google-chrome-stable", "chromium",
                    "chromium-browser", "brave-browser", "microsoft-edge", "firefox",
                    "google-chrome-beta", "google-chrome-unstable"]
        if binary in browsers:
            try:
                subprocess.Popen(
                    [binary],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                text = f"Opening {app}"
                _write_jarvis_response(text)
                return True
            except:
                pass
            # Fallback: open a URL
            open_url("https://www.google.com")
            text = f"Opening {app}"
            _write_jarvis_response(text)
            return True

        try:

            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            text = f"Opening {binary}"
            _write_jarvis_response(text)
            return True

        except:
            pass

    # ==========================================================
    # FUZZY MATCH INSTALLED BINARY
    # ==========================================================

    matched = _fuzzy_match_bin(app)
    if matched:
        try:
            subprocess.Popen(
                [matched],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            text = f"Opening {app}"
            _write_jarvis_response(text)
            return True
        except:
            pass

    # ==========================================================
    # SEARCH FALLBACK — find official site via DDG
    # ==========================================================

    opened_any = False
    try:
        url = (
            f"https://html.duckduckgo.com/html/?q="
            f"{app.replace(' ', '+')}+official+website"
        )
        response = sess.get(url, headers={"User-Agent": useragent}, timeout=4)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", class_="result__url"):
            href = link.get("href")
            if href and "uddg=" in href:
                parsed = urlparse(href)
                actual_url = parse_qs(parsed.query).get("uddg", [None])[0]
                if actual_url:
                    open_url(actual_url)
                    opened_any = True
                    text = f"Opening {app}"
                    _write_jarvis_response(text)
                    return True
    except:
        pass

    if not opened_any:
        open_url(f"https://duckduckgo.com/?q={app.replace(' ', '+')}")

    text = f"Searching for {app}"
    _write_jarvis_response(text)
    return True

# =====================================================================
# CLOSE APP
# =====================================================================

def CloseApp(app):

    try:

        subprocess.run(
            ["pkill", "-f", app.lower().strip()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        text = f"Closed {app}"
        _write_jarvis_response(text)
    
        return True

    except:

        return False

# =====================================================================
# SYSTEM CONTROLS
# =====================================================================

def System(command):

    command = command.lower()

    try:

        if "mute" in command or "unmute" in command or "volume" in command:

            if "mute" in command:
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", "toggle"],
                    stdout=subprocess.DEVNULL
                )
            elif "volume up" in command or "increase volume" in command:
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", "5%+"],
                    stdout=subprocess.DEVNULL
                )
            elif "volume down" in command or "decrease volume" in command:
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", "5%-"],
                    stdout=subprocess.DEVNULL
                )
            text = f"Volume command: {command}"
            _write_jarvis_response(text)
            return True

        elif "brightness" in command:
            if "up" in command or "increase" in command:
                subprocess.run(
                    ["brightnessctl", "s", "+5%"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            elif "down" in command or "decrease" in command:
                subprocess.run(
                    ["brightnessctl", "s", "5%-"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            text = f"Brightness command: {command}"
            _write_jarvis_response(text)
            return True

        text = f"System command: {command}"
        _write_jarvis_response(text)
        return True

    except:

        return False

# =====================================================================
# CONTENT WRITER
# =====================================================================

def Content(topic):

    topic = topic.replace("content ", "").strip()

    messages.append({
        "role": "user",
        "content": topic
    })

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=SystemChatBot + messages,
        max_tokens=2048,
        temperature=0.7,
        stream=True
    )

    answer = "".join([
        chunk.choices[0].delta.content
        for chunk in completion
        if chunk.choices[0].delta.content
    ])

    answer = answer.replace("</s>", "")

    os.makedirs("Data", exist_ok=True)

    file_path = (
        f"Data/{topic.lower().replace(' ', '_')}.txt"
    )

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(answer)

    try:

        subprocess.Popen(
            ["xdg-open", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except:
        pass

    text = f"Written content to {file_path}"
    _write_jarvis_response(text)
    return True

# =====================================================================
# WEATHER
# =====================================================================

def Weather(city=None):
    try:
        weather_ua = "curl/8.0"
        if not city or city == "weather":
            from dotenv import dotenv_values
            env = dotenv_values(".env")
            city = env.get("UserLocation", "")
        if city:
            parts = [p.strip() for p in city.split(",")]
            url = None
            # Try individual parts (most specific first), then composite
            for p in reversed(parts):
                if not re.search(r'\b(road|street|no[\s\.]?\d+|\d+$|circle|layout|colony|phase|block|sector)', p, re.IGNORECASE):
                    geo = requests.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": p + ", India", "format": "json", "limit": 1},
                        headers={"User-Agent": "JARVIS-AI/1.0"},
                        timeout=5
                    ).json()
                    if geo:
                        lat, lon = geo[0]["lat"], geo[0]["lon"]
                        url = f"https://wttr.in/{lat},{lon}?format=j1&lang=en"
                        break
            if not url:
                geo = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": city, "format": "json", "limit": 1},
                    headers={"User-Agent": "JARVIS-AI/1.0"},
                    timeout=5
                ).json()
                if geo:
                    lat, lon = geo[0]["lat"], geo[0]["lon"]
                    url = f"https://wttr.in/{lat},{lon}?format=j1&lang=en"
            if not url:
                url = "https://wttr.in?format=j1&lang=en"
        else:
            url = "https://wttr.in?format=j1&lang=en"
        response = requests.get(url, headers={"User-Agent": weather_ua}, timeout=5)
        data = response.json()
        cc = data['current_condition'][0]
        condition = cc['weatherDesc'][0]['value']
        temp = cc['temp_C']
        wind = cc['windspeedKmph']
        humidity = cc['humidity']
        feels_like = cc.get('FeelsLikeC', temp)
        result = f"It is {condition.lower()} with a temperature of {temp}°C, feels like {feels_like}°C, wind at {wind} km/h, and humidity at {humidity}%."
        weather_text = f"Weather: {result}"
        _write_jarvis_response(weather_text)
        return weather_text
    except:
        return False

# =====================================================================
# BATTERY STATUS
# =====================================================================

def BatteryStatus():
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            status = "charging" if battery.power_plugged else "on battery"
            text = f"Battery at {percent} percent, {status}"
            _write_jarvis_response(text)
        
        else:
            pass
        return True
    except:
        return False

# =====================================================================
# SCREENSHOT
# =====================================================================

def Screenshot():
    try:
        import datetime, subprocess
        os.makedirs("Screenshots", exist_ok=True)
        filename = f"Screenshots/screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        subprocess.run(["import", "-window", "root", filename], timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(filename):
            return False
        text = f"Screenshot saved as {filename}"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# LOCK COMPUTER
# =====================================================================

def LockComputer():
    try:
        subprocess.run(["loginctl", "lock-session"], timeout=3,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        text = "Locking your computer, Sir"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# TIMER
# =====================================================================

def Timer(duration_text):
    import re
    total_seconds = 0
    minutes = re.search(r'(\d+)\s*min', duration_text)
    seconds = re.search(r'(\d+)\s*sec', duration_text)
    if minutes:
        total_seconds += int(minutes.group(1)) * 60
    if seconds:
        total_seconds += int(seconds.group(1))
    if total_seconds == 0:
        try:
            total_seconds = int(duration_text.split()[-1]) * 60
        except:
            total_seconds = 60
    def _timer_done():
        TextToSpeech("Timer is up, sir.")
    threading.Timer(total_seconds, _timer_done).start()
    text = f"Timer set for {total_seconds} seconds"
    _write_jarvis_response(text)

    return True

# =====================================================================
# WIFI
# =====================================================================

def Wifi(action=None):
    try:
        if action == "on":
            subprocess.run(["nmcli", "radio", "wifi", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            text = "WiFi turned on"
        elif action == "off":
            subprocess.run(["nmcli", "radio", "wifi", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            text = "WiFi turned off"
        else:
            result = subprocess.run(["nmcli", "-t", "-f", "WIFI", "radio"], capture_output=True, text=True, timeout=3)
            status = result.stdout.strip()
            text = f"WiFi is {status}" if status else "WiFi status unknown"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# BLUETOOTH
# =====================================================================

def Bluetooth(action=None):
    try:
        if action == "on":
            subprocess.run(["bluetoothctl", "power", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            text = "Bluetooth turned on"
        elif action == "off":
            subprocess.run(["bluetoothctl", "power", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            text = "Bluetooth turned off"
        else:
            result = subprocess.run(["bluetoothctl", "show"], capture_output=True, text=True, timeout=3)
            if "Powered: yes" in result.stdout:
                text = "Bluetooth is on"
            else:
                text = "Bluetooth is off"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# NOTIFICATION
# =====================================================================

def Notify(message):
    try:
        subprocess.run(["notify-send", "Jarvis", message], timeout=3)
        text = f"Notification: {message}"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# CPU USAGE
# =====================================================================

def CpuUsage():
    try:
        import psutil
        percent = psutil.cpu_percent(interval=0.5)
        cores = psutil.cpu_count()
        text = f"CPU usage at {percent}% across {cores} cores"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# MEMORY USAGE
# =====================================================================

def MemoryUsage():
    try:
        import psutil
        mem = psutil.virtual_memory()
        text = f"RAM: {mem.used // (1024**3)}GB used of {mem.total // (1024**3)}GB total ({mem.percent}%)"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# DISK USAGE
# =====================================================================

def DiskUsage():
    try:
        import psutil, shutil
        total, used, free = shutil.disk_usage("/")
        text = f"Disk: {used // (1024**3)}GB used of {total // (1024**3)}GB total, {free // (1024**3)}GB free"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# IP ADDRESS
# =====================================================================

def IpAddress():
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        try:
            ext = requests.get("https://api.ipify.org?format=text", timeout=3).text.strip()
            text = f"Local IP: {local_ip}, Public IP: {ext}"
        except:
            text = f"Local IP: {local_ip}"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# SYSTEM UPTIME
# =====================================================================

def SystemUptime():
    try:
        result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=3)
        text = f"System uptime: {result.stdout.strip()}"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# DATE/TIME
# =====================================================================

def CurrentDateTime():
    try:
        import datetime
        now = datetime.datetime.now()
        text = now.strftime("It is %A, %B %d, %Y at %I:%M %p")
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# NOTES MANAGER
# =====================================================================

def NoteManager(action, content=None):
    try:
        notes_file = os.path.join(_AUTO_BASE, "Data", "notes.txt")
        os.makedirs(os.path.dirname(notes_file), exist_ok=True)
        if action == "read":
            if os.path.exists(notes_file):
                with open(notes_file, "r") as f:
                    notes = f.read().strip()
                text = f"Your notes:\n{notes}" if notes else "No notes saved"
            else:
                text = "No notes saved"
        elif action == "clear":
            with open(notes_file, "w") as f:
                f.write("")
            text = "All notes cleared"
        else:
            with open(notes_file, "a") as f:
                f.write(f"{content}\n")
            text = f"Note saved: {content}"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# FIND FILES
# =====================================================================

def FindFiles(name):
    try:
        home = os.path.expanduser("~")
        result = subprocess.run(
            ["find", home, "-maxdepth", "4", "-iname", f"*{name}*", "-type", "f"],
            capture_output=True, text=True, timeout=5
        )
        files = [f for f in result.stdout.strip().split('\n') if f.strip()]
        if files:
            text = f"Found {len(files)} file(s):\n" + "\n".join(files[:10])
            if len(files) > 10:
                text += f"\n... and {len(files) - 10} more"
        else:
            text = f"No files found matching '{name}'"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# EMPTY TRASH
# =====================================================================

def EmptyTrash():
    try:
        subprocess.run(["rm", "-rf", os.path.expanduser("~/.local/share/Trash/*")], shell=True, timeout=5)
        text = "Trash emptied"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# KILL PROCESS
# =====================================================================

def KillProcess(name):
    try:
        subprocess.run(["pkill", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        text = f"Process '{name}' killed"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# SET VOLUME
# =====================================================================

def VolumeSet(level):
    try:
        level = int(re.sub(r'[^0-9]', '', str(level)))
        level = max(0, min(100, level))
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        text = f"Volume set to {level}%"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# SET BRIGHTNESS
# =====================================================================

def BrightnessSet(level):
    try:
        level = int(re.sub(r'[^0-9]', '', str(level)))
        level = max(0, min(100, level))
        subprocess.run(["brightnessctl", "s", f"{level}%"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        text = f"Brightness set to {level}%"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# SCREENSAVER
# =====================================================================

def Screensaver():
    try:
        subprocess.run(["xdg-screensaver", "activate"], timeout=3,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        text = "Screensaver activated"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# MICROPHONE TOGGLE
# =====================================================================

def MicToggle(on):
    try:
        if on:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Capture", "cap"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            text = "Microphone unmuted"
        else:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Capture", "nocap"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            text = "Microphone muted"
        _write_jarvis_response(text)
    
        return True
    except:
        return False

# =====================================================================
# CLIPBOARD
# =====================================================================

def ClipboardManager(action, text=None):
    try:
        if action == "copy" and text:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), timeout=3)
            result_text = f"Copied to clipboard: {text[:50]}"
        elif action == "paste":
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                    capture_output=True, text=True, timeout=3)
            content = result.stdout.strip()
            result_text = f"Clipboard: {content[:200]}" if content else "Clipboard is empty"
        else:
            result_text = "Clipboard action not recognized"
        _write_jarvis_response(result_text)
        return True
    except:
        return False

# =====================================================================
# WEBCAM
# =====================================================================

def Webcam():
    try:
        import datetime
        os.makedirs("Screenshots", exist_ok=True)
        filename = f"Screenshots/webcam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        result = subprocess.run(["ffmpeg", "-f", "v4l2", "-i", "/dev/video0",
                                 "-frames:v", "1", filename],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        if result.returncode == 0 and os.path.exists(filename):
            text = f"Webcam photo saved as {filename}"
        else:
            text = "Could not take webcam photo"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# CALCULATOR
# =====================================================================

def Calculator(expr):
    try:
        safe = re.sub(r'[^0-9+\-*/.()% ]', '', expr)
        if not safe:
            text = "No valid expression"
        else:
            result = eval(safe, {"__builtins__": {}}, {})
            text = f"{expr} = {result}"
        _write_jarvis_response(text)
        return True
    except:
        text = f"Could not calculate '{expr}'"
        _write_jarvis_response(text)
        return False

# =====================================================================
# DICTIONARY
# =====================================================================

def DefineWord(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            meaning = data[0]["meanings"][0]
            part = meaning["partOfSpeech"]
            definition = meaning["definitions"][0]["definition"]
            text = f"{word} ({part}): {definition}"
        else:
            text = f"No definition found for '{word}'"
        _write_jarvis_response(text)
        return True
    except:
        return False

# =====================================================================
# JOKE
# =====================================================================

def TellJoke():
    try:
        url = "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            joke = r.json().get("joke", "Why did the chicken cross the road? To get to the other side.")
        else:
            joke = "Why did the chicken cross the road? To get to the other side."
        _write_jarvis_response(joke)
        return True
    except:
        return False

# =====================================================================
# FLIP COIN
# =====================================================================

def FlipCoin():
    import random
    result = random.choice(["Heads", "Tails"])
    text = f"Coin flip: {result}"
    _write_jarvis_response(text)

    return True

# =====================================================================
# FILE OPERATIONS
# =====================================================================

def FileRead(path):
    try:
        path = os.path.expanduser(path)
        with open(path, 'r') as f:
            content = f.read()
        text = f"File content: {content[:500]}"
        _write_jarvis_response(text)
        return text
    except Exception as e:
        return f"Could not read file: {e}"

def FileWrite(path, content):
    try:
        path = os.path.expanduser(path)
        with open(path, 'w') as f:
            f.write(content)
        return f"Written to {os.path.basename(path)}, Sir."
    except Exception as e:
        return f"Could not write file: {e}"

def FileDelete(path):
    try:
        path = os.path.expanduser(path)
        if os.path.isfile(path):
            os.remove(path)
            return f"Deleted {os.path.basename(path)}, Sir."
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return f"Deleted {os.path.basename(path)} and all its contents, Sir."
        return "File not found, Sir."
    except Exception as e:
        return f"Could not delete: {e}"

def FileMove(src, dst):
    try:
        src, dst = os.path.expanduser(src), os.path.expanduser(dst)
        shutil.move(src, dst)
        return f"Moved to {os.path.basename(dst)}, Sir."
    except Exception as e:
        return f"Could not move: {e}"

def FileCopy(src, dst):
    try:
        src, dst = os.path.expanduser(src), os.path.expanduser(dst)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)
        return f"Copied to {os.path.basename(dst)}, Sir."
    except Exception as e:
        return f"Could not copy: {e}"

def FolderCreate(path):
    try:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
        return f"Created folder {os.path.basename(path)}, Sir."
    except Exception as e:
        return f"Could not create folder: {e}"

# =====================================================================
# WINDOW MANAGEMENT
# =====================================================================

def WindowMinimize():
    subprocess.run(["xdotool", "getactivewindow", "windowminimize"], capture_output=True)
    return "Window minimized, Sir."

def WindowMaximize():
    subprocess.run(["xdotool", "getactivewindow", "windowstate", "--toggle", "MAXIMIZED_VERT", "MAXIMIZED_HORZ"], capture_output=True)
    return "Window maximized, Sir."

def WindowClose():
    subprocess.run(["xdotool", "getactivewindow", "windowkill"], capture_output=True)
    return "Window closed, Sir."

def WindowMove(x, y):
    subprocess.run(["xdotool", "getactivewindow", "windowmove", str(x), str(y)], capture_output=True)
    return f"Window moved to {x}, {y}, Sir."

def WindowResize(w, h):
    subprocess.run(["xdotool", "getactivewindow", "windowsize", str(w), str(h)], capture_output=True)
    return f"Window resized to {w}x{h}, Sir."

# =====================================================================
# KEYBOARD & MOUSE
# =====================================================================

def TypeText(text):
    subprocess.run(["xdotool", "type", "--", text], capture_output=True)
    return f"Typed: {text[:50]}"

def PressKey(key):
    subprocess.run(["xdotool", "key", key], capture_output=True)
    return f"Pressed {key}"

def MouseClick(button="1"):
    subprocess.run(["xdotool", "click", button], capture_output=True)
    return "Clicked, Sir."

def MouseMove(x, y):
    subprocess.run(["xdotool", "mousemove", str(x), str(y)], capture_output=True)
    return f"Mouse moved to {x}, {y}, Sir."

def MouseScroll(clicks):
    direction = "4" if int(clicks) > 0 else "5"
    for _ in range(abs(int(clicks))):
        subprocess.run(["xdotool", "click", direction], capture_output=True)
    return f"Scrolled {clicks} clicks, Sir."

# =====================================================================
# SYSTEM COMMANDS
# =====================================================================

def Shutdown(delay=0):
    subprocess.run(["shutdown", f"+{delay}"], capture_output=True)
    return "Shutting down, Sir."

def Restart():
    subprocess.run(["shutdown", "-r", "now"], capture_output=True)
    return "Restarting, Sir."

def Sleep():
    subprocess.run(["systemctl", "suspend"], capture_output=True)
    return "Going to sleep, Sir."

def LockScreen():
    subprocess.run(["loginctl", "lock-session"], capture_output=True)
    return "Screen locked, Sir."

# =====================================================================
# BROWSER CONTROL
# =====================================================================

def BrowserNavigate(url):
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.run(["xdotool", "key", "ctrl+l"], capture_output=True)
    subprocess.run(["xdotool", "type", "--", url], capture_output=True)
    subprocess.run(["xdotool", "key", "Return"], capture_output=True)
    return f"Navigating to {url}, Sir."

def BrowserBack():
    subprocess.run(["xdotool", "key", "alt+Left"], capture_output=True)
    return "Going back, Sir."

def BrowserForward():
    subprocess.run(["xdotool", "key", "alt+Right"], capture_output=True)
    return "Going forward, Sir."

def BrowserRefresh():
    subprocess.run(["xdotool", "key", "ctrl+r"], capture_output=True)
    return "Refreshed, Sir."

def BrowserScrollDown():
    subprocess.run(["xdotool", "key", "Page_Down"], capture_output=True)
    return "Scrolled down, Sir."

def BrowserScrollUp():
    subprocess.run(["xdotool", "key", "Page_Up"], capture_output=True)
    return "Scrolled up, Sir."

def BrowserNewTab():
    subprocess.run(["xdotool", "key", "ctrl+t"], capture_output=True)
    return "New tab opened, Sir."

def BrowserCloseTab():
    subprocess.run(["xdotool", "key", "ctrl+w"], capture_output=True)
    return "Tab closed, Sir."

def BrowserSwitchTab(n):
    for _ in range(int(n)):
        subprocess.run(["xdotool", "key", "ctrl+Tab"], capture_output=True)
    return f"Switched to tab {n}, Sir."

# =====================================================================
# PROCESS
# =====================================================================

def ProcessList():
    try:
        result = subprocess.run(["ps", "aux", "--sort=-%mem"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")[1:11]
        output = "\n".join(lines[:10])
        text = f"Top processes:\n{output}"
        _write_jarvis_response(text)
        return text
    except Exception as e:
        return f"Could not list processes: {e}"

def ProcessKill(name):
    try:
        subprocess.run(["pkill", "-f", name], capture_output=True)
        return f"Killed {name}, Sir."
    except Exception as e:
        return f"Could not kill process: {e}"

# =====================================================================
# MISC
# =====================================================================

def ExecuteShell(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip()[:500] or "Done, Sir."
        _write_jarvis_response(output)
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out, Sir."
    except Exception as e:
        return f"Command failed: {e}"

# =====================================================================
# ASYNC ROUTER
# =====================================================================

async def TranslateAndExecute(commands: list[str]):

    funcs = []

    commands = list(dict.fromkeys(commands))

    for command in commands:

        cmd = command.lower().strip()

        # ==========================================================
        # OPEN
        # ==========================================================

        if cmd.startswith("open "):

            app_name = cmd.replace("open ", "").strip()
            funcs.append(
                asyncio.to_thread(OpenApp, app_name)
            )

        # ==========================================================
        # CLOSE
        # ==========================================================

        elif cmd.startswith("close "):

            app_name = cmd.replace("close ", "").strip()
            funcs.append(
                asyncio.to_thread(CloseApp, app_name)
            )

        # ==========================================================
        # PLAY
        # ==========================================================

        elif cmd.startswith("play "):

            query = cmd.replace("play ", "").strip()
            funcs.append(
                asyncio.to_thread(PlayYoutube, query)
            )

        # ==========================================================
        # GOOGLE SEARCH
        # ==========================================================

        elif "google search" in cmd:

            topic = cmd.replace("google search", "").strip()
            funcs.append(
                asyncio.to_thread(GoogleSearch, topic)
            )

        # ==========================================================
        # YOUTUBE SEARCH
        # ==========================================================

        elif "youtube search" in cmd:

            topic = cmd.replace("youtube search", "").strip()
            funcs.append(
                asyncio.to_thread(YoutubeSearch, topic)
            )

        # ==========================================================
        # CONTENT
        # ==========================================================

        elif cmd.startswith(("content ", "write ")):

            funcs.append(
                asyncio.to_thread(Content, cmd)
            )

        # ==========================================================
        # SYSTEM
        # ==========================================================

        elif cmd.startswith("system "):

            funcs.append(
                asyncio.to_thread(
                    System,
                    cmd.replace("system ", "")
                )
            )

        # ==========================================================
        # WEATHER
        # ==========================================================

        elif cmd.startswith("weather"):

            city = cmd.replace("weather", "").strip()
            funcs.append(
                asyncio.to_thread(Weather, city or None)
            )

        # ==========================================================
        # BATTERY
        # ==========================================================

        elif "battery" in cmd:

            funcs.append(
                asyncio.to_thread(BatteryStatus)
            )

        # ==========================================================
        # SCREENSHOT
        # ==========================================================

        elif "screenshot" in cmd:

            funcs.append(
                asyncio.to_thread(Screenshot)
            )

        # ==========================================================
        # LOCK
        # ==========================================================

        elif "lock" in cmd:

            funcs.append(
                asyncio.to_thread(LockComputer)
            )

        # ==========================================================
        # TIMER
        # ==========================================================

        elif cmd.startswith("timer"):

            duration = cmd.replace("timer", "").strip()
            funcs.append(
                asyncio.to_thread(Timer, duration)
            )

        # ==========================================================
        # WIFI
        # ==========================================================

        elif cmd.startswith("wifi"):
            action = cmd.replace("wifi", "").strip()
            funcs.append(asyncio.to_thread(Wifi, action if action else None))

        # ==========================================================
        # BLUETOOTH
        # ==========================================================

        elif cmd.startswith("bluetooth"):
            action = cmd.replace("bluetooth", "").strip()
            funcs.append(asyncio.to_thread(Bluetooth, action if action else None))

        # ==========================================================
        # NOTIFICATION
        # ==========================================================

        elif cmd.startswith("notify"):
            msg = cmd.replace("notify", "").strip()
            if msg:
                funcs.append(asyncio.to_thread(Notify, msg))

        # ==========================================================
        # CPU
        # ==========================================================

        elif cmd == "cpu":
            funcs.append(asyncio.to_thread(CpuUsage))

        # ==========================================================
        # MEMORY
        # ==========================================================

        elif cmd == "memory":
            funcs.append(asyncio.to_thread(MemoryUsage))

        # ==========================================================
        # DISK
        # ==========================================================

        elif cmd == "disk":
            funcs.append(asyncio.to_thread(DiskUsage))

        # ==========================================================
        # IP
        # ==========================================================

        elif cmd == "ip":
            funcs.append(asyncio.to_thread(IpAddress))

        # ==========================================================
        # UPTIME
        # ==========================================================

        elif cmd == "uptime":
            funcs.append(asyncio.to_thread(SystemUptime))

        # ==========================================================
        # DATE/TIME
        # ==========================================================

        elif cmd == "datetime":
            funcs.append(asyncio.to_thread(CurrentDateTime))

        # ==========================================================
        # NOTES
        # ==========================================================

        elif cmd.startswith("note"):
            rest = cmd.replace("note", "").strip()
            if rest == "read":
                funcs.append(asyncio.to_thread(NoteManager, "read"))
            elif rest == "clear":
                funcs.append(asyncio.to_thread(NoteManager, "clear"))
            elif rest:
                funcs.append(asyncio.to_thread(NoteManager, "save", rest))
            else:
                funcs.append(asyncio.to_thread(NoteManager, "read"))

        # ==========================================================
        # FIND FILES
        # ==========================================================

        elif cmd.startswith("find"):
            name = cmd.replace("find", "").strip()
            if name:
                funcs.append(asyncio.to_thread(FindFiles, name))

        # ==========================================================
        # EMPTY TRASH
        # ==========================================================

        elif cmd == "emptytrash":
            funcs.append(asyncio.to_thread(EmptyTrash))

        # ==========================================================
        # KILL PROCESS
        # ==========================================================

        elif cmd.startswith("kill"):
            name = cmd.replace("kill", "").strip()
            if name:
                funcs.append(asyncio.to_thread(KillProcess, name))

        # ==========================================================
        # VOLUME SET
        # ==========================================================

        elif cmd.startswith("volume"):
            rest = cmd.replace("volume", "").strip()
            if "set" in rest:
                level = rest.replace("set", "").strip()
                funcs.append(asyncio.to_thread(VolumeSet, level))

        # ==========================================================
        # BRIGHTNESS SET
        # ==========================================================

        elif cmd.startswith("brightness"):
            rest = cmd.replace("brightness", "").strip()
            if "set" in rest:
                level = rest.replace("set", "").strip()
                funcs.append(asyncio.to_thread(BrightnessSet, level))

        # ==========================================================
        # SCREENSAVER
        # ==========================================================

        elif cmd == "screensaver":
            funcs.append(asyncio.to_thread(Screensaver))

        # ==========================================================
        # MIC TOGGLE
        # ==========================================================

        elif cmd.startswith("mic"):
            rest = cmd.replace("mic", "").strip()
            funcs.append(asyncio.to_thread(MicToggle, rest != "off"))

        # ==========================================================
        # CLIPBOARD
        # ==========================================================

        elif cmd.startswith("clipboard"):
            rest = cmd.replace("clipboard", "").strip()
            if rest.startswith("copy"):
                text = rest.replace("copy", "").strip()
                funcs.append(asyncio.to_thread(ClipboardManager, "copy", text))
            else:
                funcs.append(asyncio.to_thread(ClipboardManager, "paste"))

        # ==========================================================
        # WEBCAM
        # ==========================================================

        elif cmd == "webcam":
            funcs.append(asyncio.to_thread(Webcam))

        # ==========================================================
        # CALCULATOR
        # ==========================================================

        elif cmd.startswith("calc"):
            expr = cmd.replace("calc", "").strip()
            if expr:
                funcs.append(asyncio.to_thread(Calculator, expr))

        # ==========================================================
        # DEFINE
        # ==========================================================

        elif cmd.startswith("define"):
            word = cmd.replace("define", "").strip()
            if word:
                funcs.append(asyncio.to_thread(DefineWord, word))

        # ==========================================================
        # JOKE
        # ==========================================================

        elif cmd == "joke":
            funcs.append(asyncio.to_thread(TellJoke))

        # ==========================================================
        # FLIP COIN
        # ==========================================================

        elif cmd == "flip":
            funcs.append(asyncio.to_thread(FlipCoin))

        # ==========================================================
        # FILE OPERATIONS
        # ==========================================================

        elif cmd.startswith("read file "):
            path = cmd.replace("read file ", "").strip()
            funcs.append(asyncio.to_thread(FileRead, path))

        elif cmd.startswith("write file "):
            rest = cmd.replace("write file ", "").strip()
            if " to " in rest:
                content, path = rest.split(" to ", 1)
                funcs.append(asyncio.to_thread(FileWrite, path.strip(), content.strip()))

        elif cmd.startswith("delete "):
            path = cmd.replace("delete ", "").strip()
            funcs.append(asyncio.to_thread(FileDelete, path))

        elif cmd.startswith("move "):
            rest = cmd.replace("move ", "").strip()
            if " to " in rest:
                src, dst = rest.split(" to ", 1)
                funcs.append(asyncio.to_thread(FileMove, src.strip(), dst.strip()))

        elif cmd.startswith("copy "):
            rest = cmd.replace("copy ", "").strip()
            if " to " in rest:
                src, dst = rest.split(" to ", 1)
                funcs.append(asyncio.to_thread(FileCopy, src.strip(), dst.strip()))

        elif cmd.startswith("create folder "):
            path = cmd.replace("create folder ", "").strip()
            funcs.append(asyncio.to_thread(FolderCreate, path))

        # ==========================================================
        # WINDOW MANAGEMENT
        # ==========================================================

        elif "minimize window" in cmd:
            funcs.append(asyncio.to_thread(WindowMinimize))

        elif "maximize window" in cmd:
            funcs.append(asyncio.to_thread(WindowMaximize))

        elif "close window" in cmd:
            funcs.append(asyncio.to_thread(WindowClose))

        # ==========================================================
        # KEYBOARD & MOUSE
        # ==========================================================

        elif cmd.startswith("type "):
            text = cmd.replace("type ", "").strip()
            funcs.append(asyncio.to_thread(TypeText, text))

        elif cmd.startswith("press "):
            key = cmd.replace("press ", "").strip()
            funcs.append(asyncio.to_thread(PressKey, key))

        elif cmd.startswith("click"):
            funcs.append(asyncio.to_thread(MouseClick))

        elif cmd.startswith("scroll "):
            rest = cmd.replace("scroll ", "").strip()
            if rest.startswith("up"):
                funcs.append(asyncio.to_thread(MouseScroll, "-3"))
            elif rest.startswith("down"):
                funcs.append(asyncio.to_thread(MouseScroll, "3"))

        # ==========================================================
        # SYSTEM
        # ==========================================================

        elif "shutdown" in cmd:
            funcs.append(asyncio.to_thread(Shutdown))

        elif "restart" in cmd and "browser" not in cmd:
            funcs.append(asyncio.to_thread(Restart))

        elif "sleep" in cmd or "suspend" in cmd:
            funcs.append(asyncio.to_thread(Sleep))

        elif "lock screen" in cmd:
            funcs.append(asyncio.to_thread(LockScreen))

        # ==========================================================
        # BROWSER CONTROL
        # ==========================================================

        elif cmd.startswith("go to "):
            url = cmd.replace("go to ", "").strip()
            funcs.append(asyncio.to_thread(BrowserNavigate, url))

        elif cmd.startswith("navigate to "):
            url = cmd.replace("navigate to ", "").strip()
            funcs.append(asyncio.to_thread(BrowserNavigate, url))

        elif "browser back" in cmd or "go back" in cmd:
            funcs.append(asyncio.to_thread(BrowserBack))

        elif "browser forward" in cmd or "go forward" in cmd:
            funcs.append(asyncio.to_thread(BrowserForward))

        elif "refresh" in cmd or "reload" in cmd:
            funcs.append(asyncio.to_thread(BrowserRefresh))

        elif "scroll down" in cmd:
            funcs.append(asyncio.to_thread(BrowserScrollDown))

        elif "scroll up" in cmd:
            funcs.append(asyncio.to_thread(BrowserScrollUp))

        elif "new tab" in cmd:
            funcs.append(asyncio.to_thread(BrowserNewTab))

        elif "close tab" in cmd:
            funcs.append(asyncio.to_thread(BrowserCloseTab))

        elif cmd.startswith("switch tab "):
            n = cmd.replace("switch tab ", "").strip()
            funcs.append(asyncio.to_thread(BrowserSwitchTab, n))

        # ==========================================================
        # PROCESS
        # ==========================================================

        elif cmd == "process list" or cmd == "list processes":
            funcs.append(asyncio.to_thread(ProcessList))

        elif cmd.startswith("kill process "):
            name = cmd.replace("kill process ", "").strip()
            funcs.append(asyncio.to_thread(ProcessKill, name))

        # ==========================================================
        # SHELL
        # ==========================================================

        elif cmd.startswith("shell "):
            command = cmd.replace("shell ", "").strip()
            funcs.append(asyncio.to_thread(ExecuteShell, command))

        else:

            print(f"[red]No Function Found:[/red] {cmd}")

    results = await asyncio.gather(*funcs)

    for result in results:
        yield result

# =====================================================================
# MAIN AUTOMATION
# =====================================================================

async def Automation(commands: list[str]):

    async for _ in TranslateAndExecute(commands):
        pass

    return True

# =====================================================================
# TEST
# =====================================================================

if __name__ == "__main__":
    asyncio.run(Automation(""))
