import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os, sys, threading, time, io, base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

# TTS state
_speaking = False
_speaking_lock = threading.Lock()
_tts_quiet_until = 0.0  # Don't listen until this timestamp (cooldown after TTS)

web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Frontend", "web")
os.makedirs(web_dir, exist_ok=True)

from fastapi.responses import FileResponse
import mimetypes

@app.get("/{filename:path}")
async def serve_static(filename: str):
    filepath = os.path.join(web_dir, filename)
    if os.path.isfile(filepath):
        media_type, _ = mimetypes.guess_type(filepath)
        return FileResponse(filepath, media_type=media_type)
    return HTMLResponse(content=open(os.path.join(web_dir, "index.html")).read())

# =====================================================================
# STT ENDPOINT — server-side speech recognition for QtWebEngine & fallback
# =====================================================================

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        import speech_recognition as sr
        audio_bytes = await file.read()
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        return JSONResponse({"text": text, "success": True})
    except sr.UnknownValueError:
        return JSONResponse({"text": "", "success": False, "error": "Could not understand audio"})
    except Exception as e:
        return JSONResponse({"text": "", "success": False, "error": str(e)})

@app.post("/api/stt-base64")
async def speech_to_text_base64(data: dict):
    try:
        import speech_recognition as sr
        audio_b64 = data.get("audio", "")
        audio_bytes = base64.b64decode(audio_b64)
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        return JSONResponse({"text": text, "success": True})
    except sr.UnknownValueError:
        return JSONResponse({"text": "", "success": False, "error": "Could not understand audio"})
    except Exception as e:
        return JSONResponse({"text": "", "success": False, "error": str(e)})

@app.get("/", response_class=HTMLResponse)
async def get():
    with open(os.path.join(web_dir, "index.html"), "r") as f:
        return f.read()

def _process_query(text):
    from Backend.Model import FirstLayerDMM
    from Backend.RealtimeSearchEngine import RealtimeSearchEngine
    from Backend.Chatbot import ChatBot
    from Backend.Memory import save_memory
    import json, traceback

    Decision = FirstLayerDMM(text)
    if not Decision:
        return "On it, sir."

    if "near me" in text.lower():
        for i, d in enumerate(Decision):
            if d.lower().startswith("google search"):
                Decision[i] = "realtime " + d[len("google search"):].strip()

    Functions = ["open", "close", "play", "system", "content", "google search", "youtube search", "weather", "battery", "screenshot", "lock", "timer", "brightness", "datetime", "cpu", "memory", "disk", "ip", "uptime", "note", "find", "emptytrash", "kill", "volume", "screensaver", "mic", "clipboard", "webcam", "calc", "define", "joke", "notify", "wifi", "bluetooth", "read file", "write file", "delete", "move", "copy", "create folder", "minimize window", "maximize window", "close window", "type", "press", "click", "scroll", "shutdown", "restart", "sleep", "lock screen", "go to", "navigate to", "browser back", "browser forward", "refresh", "reload", "new tab", "close tab", "switch tab", "process list", "kill process", "shell"]
    task_items = [d for d in Decision if any(d.startswith(func) for func in Functions)]
    G = any(d.startswith("general") for d in Decision)
    R = any(d.startswith("realtime") for d in Decision)

    responses = []

    # --- Run automation tasks ---
    if task_items:
        try:
            auto_result = _run_automation_sync(task_items)
            if auto_result:
                responses.append(auto_result)
        except Exception as e:
            responses.append(f"Command error: {traceback.format_exc()}")

    # --- Get conversational response (general/realtime) ---
    if G or R:
        conv_parts = []
        for d in Decision:
            if d.startswith("general"):
                query = d.replace("general", "", 1).strip()
                if query:
                    conv_parts.append(query)
            elif d.startswith("realtime"):
                query = d.replace("realtime", "", 1).strip()
                if query:
                    conv_parts.append(query)
        conv_query = " and ".join(conv_parts) if conv_parts else text
        conv_result = ""
        if R:
            conv_result = RealtimeSearchEngine(conv_query)
        if G and not conv_result:
            conv_result = ChatBot(conv_query)
        if conv_result:
            responses.append(conv_result)

    result = " — ".join(responses) if responses else "On it, sir."

    # --- Save to ChatLog (single user + single assistant) ---
    try:
        with open(r"Data/ChatLog.json", "r") as f:
            chat = json.load(f)
    except:
        chat = []
    chat.append({"role": "user", "content": text})
    chat.append({"role": "assistant", "content": result})
    if len(chat) > 50:
        chat = chat[-50:]
    with open(r"Data/ChatLog.json", "w") as f:
        json.dump(chat, f, indent=4)

    return result

def _run_automation_sync(commands):
    """Run automation commands synchronously and capture the response."""
    from Backend.Automation import Weather, BatteryStatus, Timer, Screenshot, LockComputer, OpenApp, CloseApp, PlayYoutube, GoogleSearch, YoutubeSearch, System, Notify, CpuUsage, MemoryUsage, DiskUsage, IpAddress, SystemUptime, CurrentDateTime, NoteManager, FindFiles, VolumeSet, BrightnessSet, Wifi, Bluetooth, MicToggle, ClipboardManager, Webcam, Calculator, DefineWord, TellJoke, FlipCoin, EmptyTrash, KillProcess, Screensaver, Content
    import subprocess, re

    _RESP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Frontend", "Files", "Responses.data")

    def _read_last_response():
        try:
            with open(_RESP_FILE, "r") as f:
                lines = f.read().strip().split("\n")
                for line in reversed(lines):
                    if "Jarvis:" in line:
                        return line.split("Jarvis:", 1)[1].strip()
        except:
            pass
        return ""

    results = []
    open_apps = []
    close_apps = []
    for cmd_raw in commands:
        cmd = cmd_raw.strip()
        if cmd.startswith("open "):
            app_name = cmd.replace("open ", "").strip()
            threading.Thread(target=OpenApp, args=(app_name,), daemon=True).start()
            open_apps.append(app_name)
        elif cmd.startswith("close "):
            app_name = cmd.replace("close ", "").strip()
            CloseApp(app_name)
            close_apps.append(app_name)
        elif cmd.startswith("play "):
            query = cmd.replace("play ", "").strip()
            PlayYoutube(query)
            results.append(f"Playing {query}, Sir.")
        elif cmd.startswith("weather"):
            city = cmd.replace("weather", "").strip()
            r = Weather(city if city else None)
            if isinstance(r, str):
                results.append(r)
            elif r is True:
                results.append(_read_last_response() or "Weather checked, Sir.")
        elif cmd.startswith("battery"):
            r = BatteryStatus()
            if isinstance(r, str):
                results.append(r)
            elif r is True:
                results.append(_read_last_response() or "Battery checked, Sir.")
        elif cmd.startswith("timer"):
            duration = cmd.replace("timer", "").strip()
            Timer(duration)
            results.append(f"Timer set for {duration}")
        elif cmd.startswith("screenshot"):
            Screenshot()
            results.append("Screenshot taken, Sir.")
        elif cmd.startswith("lock"):
            LockComputer()
            results.append("Locking the system, Sir.")
        elif cmd.startswith("google search"):
            topic = cmd.replace("google search", "").strip()
            GoogleSearch(topic)
            results.append(f"Searched Google for {topic}")
        elif cmd.startswith("youtube search"):
            topic = cmd.replace("youtube search", "").strip()
            YoutubeSearch(topic)
            results.append(f"Searched YouTube for {topic}")
        elif cmd.startswith("brightness"):
            level = cmd.replace("brightness", "").strip()
            if level:
                subprocess.run(["brightnessctl", "set", level + "%"], capture_output=True)
                results.append(f"Brightness set to {level} percent.")
            else:
                results.append("Adjusting brightness, Sir.")
        elif cmd.startswith("system"):
            rest = cmd.replace("system", "").strip()
            results.append("System command executed, Sir.")
        elif cmd.startswith("notify"):
            msg = cmd.replace("notify", "").strip()
            Notify(msg)
            results.append(f"Notification sent")
        elif cmd.startswith("volume"):
            rest = cmd.replace("volume", "").strip()
            VolumeSet(rest)
            results.append(f"Volume adjusted")
        elif cmd.startswith("wifi"):
            action = cmd.replace("wifi", "").strip()
            Wifi(action if action else None)
            results.append("WiFi command executed")
        elif cmd.startswith("bluetooth"):
            action = cmd.replace("bluetooth", "").strip()
            Bluetooth(action if action else None)
            results.append("Bluetooth command executed")
        elif cmd in ("cpu", "memory", "disk", "ip", "uptime", "datetime"):
            {
                "cpu": CpuUsage,
                "memory": MemoryUsage,
                "disk": DiskUsage,
                "ip": IpAddress,
                "uptime": SystemUptime,
                "datetime": CurrentDateTime,
            }[cmd]()
            results.append(f"{cmd.capitalize()} checked, Sir.")
        elif cmd.startswith("note"):
            rest = cmd.replace("note", "").strip()
            if rest == "read":
                NoteManager("read")
            elif rest == "clear":
                NoteManager("clear")
            elif rest:
                NoteManager("save", rest)
            results.append("Note command executed")
        elif cmd.startswith("emptytrash"):
            EmptyTrash()
            results.append("Trash emptied, Sir.")
        elif cmd.startswith("kill"):
            proc = cmd.replace("kill", "").strip()
            KillProcess(proc)
            results.append(f"Killed {proc}")
        elif cmd.startswith("calc"):
            expr = cmd.replace("calc", "").strip()
            Calculator(expr)
            results.append(f"Calculated")
        elif cmd.startswith("define"):
            word = cmd.replace("define", "").strip()
            DefineWord(word)
            results.append(f"Defined {word}")
        elif cmd.startswith("joke"):
            TellJoke()
            results.append("Joke told, Sir.")
        elif cmd.startswith("flip"):
            FlipCoin()
            results.append("Coin flipped, Sir.")
        elif cmd.startswith("mic"):
            rest = cmd.replace("mic", "").strip()
            MicToggle(rest != "off")
            results.append("Mic toggled")
        elif cmd.startswith("clipboard"):
            rest = cmd.replace("clipboard", "").strip()
            if rest.startswith("copy"):
                text = rest.replace("copy", "").strip()
                ClipboardManager("copy", text)
            else:
                ClipboardManager("paste")
            results.append("Clipboard command executed")
        elif cmd.startswith("webcam"):
            Webcam()
            results.append("Webcam photo taken, Sir.")
        elif cmd.startswith("screensaver"):
            Screensaver()
            results.append("Screensaver activated")
        elif cmd.startswith("content"):
            topic = cmd.replace("content", "").strip()
            Content(topic if topic else "untitled")
            results.append(f"Content written, Sir.")
        else:
            asyncio.run(_run_automation_async([cmd]))
            results.append(f"Executing: {cmd}")

    if open_apps:
        if len(open_apps) == 1:
            results.append(f"Opening {open_apps[0]}, Sir.")
        elif len(open_apps) == 2:
            results.append(f"Opening {open_apps[0]} and {open_apps[1]}, Sir.")
        else:
            results.append(f"Opening {', '.join(open_apps[:-1])}, and {open_apps[-1]}, Sir.")
    if close_apps:
        if len(close_apps) == 1:
            results.append(f"Closed {close_apps[0]}, Sir.")
        elif len(close_apps) == 2:
            results.append(f"Closed {close_apps[0]} and {close_apps[1]}, Sir.")
        else:
            results.append(f"Closed {', '.join(close_apps[:-1])}, and {close_apps[-1]}, Sir.")
    return " — ".join(results) if results else "Done, Sir."

def _speak_tts(text, on_done=None):
    """Play TTS on the server — only first line."""
    global _speaking, _tts_quiet_until
    try:
        from Backend.TextToSpeech import TextToSpeech
        first = text.split(".")[0].strip()
        if first:
            with _speaking_lock:
                _speaking = True
            TextToSpeech(first, func=lambda: _speaking)
            with _speaking_lock:
                _speaking = False
                _tts_quiet_until = time.time() + 0.6
    except:
        with _speaking_lock:
            _speaking = False
            _tts_quiet_until = time.time() + 0.6
    finally:
        if on_done:
            on_done()

def _stop_speaking():
    """Stop current TTS playback."""
    global _speaking, _tts_quiet_until
    with _speaking_lock:
        _speaking = False
        _tts_quiet_until = time.time() + 0.6
    try:
        from Backend.TextToSpeech import stop_tts
        stop_tts()
    except:
        pass

async def _run_automation_async(commands):
    """Run automation commands asynchronously using the Automation pipeline."""
    from Backend.Automation import Automation
    await Automation(commands)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "status", "text": "CONNECTED. AT YOUR SERVICE, SIR."})
    _listening = threading.Event()
    _loop = asyncio.get_event_loop()

    def _try_silent_command(text):
        """Execute a direct automation command silently. Returns True if matched."""
        from Backend.Automation import OpenApp, CloseApp, PlayYoutube, Weather, BatteryStatus, Timer, Screenshot, LockComputer, GoogleSearch, YoutubeSearch, System, Notify, CpuUsage, MemoryUsage, DiskUsage, IpAddress, SystemUptime, CurrentDateTime, NoteManager, FindFiles, VolumeSet, BrightnessSet, Wifi, Bluetooth, MicToggle, ClipboardManager, Webcam, Calculator, DefineWord, TellJoke, FlipCoin, EmptyTrash, KillProcess, Screensaver, Content
        import subprocess
        cmd = text.lower().strip()
        if cmd.startswith("open "):
            app = cmd[5:].strip()
            if app: threading.Thread(target=OpenApp, args=(app,), daemon=True).start()
            return True
        if cmd.startswith("close "):
            app = cmd[6:].strip()
            if app: CloseApp(app)
            return True
        if cmd.startswith("play "):
            q = cmd[5:].strip()
            if q: PlayYoutube(q)
            return True
        if cmd.startswith("weather"):
            Weather(cmd[7:].strip() or None)
            return True
        if cmd.startswith("battery"):
            BatteryStatus()
            return True
        if cmd.startswith("timer"):
            Timer(cmd[5:].strip())
            return True
        if cmd.startswith("screenshot"):
            Screenshot()
            return True
        if cmd.startswith("lock"):
            LockComputer()
            return True
        if cmd.startswith("google search"):
            q = cmd[14:].strip()
            if q: GoogleSearch(q)
            return True
        if cmd.startswith("youtube search"):
            q = cmd[15:].strip()
            if q: YoutubeSearch(q)
            return True
        if cmd.startswith("brightness"):
            lvl = cmd[10:].strip()
            if lvl: subprocess.run(["brightnessctl", "set", lvl + "%"], capture_output=True)
            return True
        if cmd.startswith("system"):
            System(cmd[6:].strip())
            return True
        if cmd.startswith("notify"):
            msg = cmd[6:].strip()
            if msg: Notify(msg)
            return True
        if cmd.startswith("volume"):
            VolumeSet(cmd[6:].strip())
            return True
        if cmd.startswith("wifi"):
            Wifi(cmd[4:].strip() or None)
            return True
        if cmd.startswith("bluetooth"):
            Bluetooth(cmd[9:].strip() or None)
            return True
        if cmd in ("cpu", "memory", "disk", "ip", "uptime", "datetime"):
            {"cpu": CpuUsage, "memory": MemoryUsage, "disk": DiskUsage, "ip": IpAddress, "uptime": SystemUptime, "datetime": CurrentDateTime}[cmd]()
            return True
        if cmd.startswith("note"):
            rest = cmd[4:].strip()
            if rest == "read": NoteManager("read")
            elif rest == "clear": NoteManager("clear")
            elif rest: NoteManager("save", rest)
            return True
        if cmd.startswith("emptytrash"):
            EmptyTrash()
            return True
        if cmd.startswith("kill"):
            proc = cmd[4:].strip()
            if proc: KillProcess(proc)
            return True
        if cmd.startswith("calc"):
            expr = cmd[4:].strip()
            if expr: Calculator(expr)
            return True
        if cmd.startswith("define"):
            word = cmd[6:].strip()
            if word: DefineWord(word)
            return True
        if cmd.startswith("joke"):
            TellJoke()
            return True
        if cmd.startswith("flip"):
            FlipCoin()
            return True
        if cmd.startswith("mic"):
            rest = cmd[3:].strip()
            MicToggle(rest != "off")
            return True
        if cmd.startswith("clipboard"):
            rest = cmd[9:].strip()
            if rest.startswith("copy"):
                ClipboardManager("copy", rest[4:].strip())
            else:
                ClipboardManager("paste")
            return True
        if cmd.startswith("webcam"):
            Webcam()
            return True
        if cmd.startswith("screensaver"):
            Screensaver()
            return True
        if cmd.startswith("content"):
            Content(cmd[7:].strip() or "untitled")
            return True
        return False

    def _server_listen():
        from Backend.SpeechToText import AudioStream, transcribe_wav, QueryModifier
        stream = None
        try:
            stream = AudioStream().open()
            accumulated = []
            while _listening.is_set():
                # Block listening during TTS playback and echo cooldown
                if _speaking or time.time() < _tts_quiet_until:
                    if stream:
                        stream.close()
                        stream = None
                    time.sleep(0.05)
                    continue
                if stream is None:
                    stream = AudioStream().open()
                # stop_check aborts capture_speech the moment TTS starts
                wav_bytes = stream.capture_speech(
                    stop_check=lambda: _speaking or time.time() < _tts_quiet_until
                )
                if not wav_bytes:
                    continue
                text = transcribe_wav(wav_bytes)
                if not text:
                    continue
                text = QueryModifier(text)
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "server_transcript", "text": text}),
                    _loop
                )
                clean = text.lower().strip().rstrip('.!?,;:')
                if _try_silent_command(clean):
                    print(f"Silent command: {clean}")
                    continue
                accumulated.append(text)
                # Quiescence: if TTS or user continued, skip processing
                if _speaking or time.time() < _tts_quiet_until or stream.has_speech(1):
                    continue
                if accumulated:
                    full = " ".join(accumulated)
                    accumulated.clear()
                    result = _process_query(full)
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "response",
                            "text": result,
                            "user_text": full,
                            "speak": True
                        }),
                        _loop
                    )
                    if result:
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({"type": "speaking_state", "speaking": True}),
                            _loop
                        )
                        def _on_done():
                            asyncio.run_coroutine_threadsafe(
                                websocket.send_json({"type": "speaking_state", "speaking": False}),
                                _loop
                            )
                        threading.Thread(target=_speak_tts, args=(result, _on_done), daemon=True).start()
        except Exception as e:
            print(f"Mic error: {e}")
        finally:
            if stream:
                stream.close()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            text = data.get("text", "").strip()

            if msg_type == "server_mic_start":
                _listening.set()
                threading.Thread(target=_server_listen, daemon=True).start()
                await websocket.send_json({"type": "status", "text": "Server mic activated..."})
                continue

            if msg_type == "server_mic_stop":
                _listening.clear()
                await websocket.send_json({"type": "status", "text": "Server mic deactivated"})
                continue

            if msg_type == "stop_speaking":
                _stop_speaking()
                await websocket.send_json({"type": "status", "text": "Speech stopped"})
                continue

            if not text:
                if msg_type == "speech":
                    await websocket.send_json({"type": "error", "text": "I didn't catch that, Sir."})
                continue

            # Interrupt TTS if speaking so user can ask something new
            with _speaking_lock:
                if _speaking:
                    _stop_speaking()
                    await websocket.send_json({"type": "speaking_state", "speaking": False})

            await websocket.send_json({"type": "status", "text": "Thinking..."})

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _process_query, text)

            if result:
                await websocket.send_json({"type": "speaking_state", "speaking": True})

            await websocket.send_json({
                "type": "response",
                "text": result,
                "speak": bool(result)
            })

            if result:
                await websocket.send_json({"type": "speaking_state", "speaking": True})
                def _on_done():
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({"type": "speaking_state", "speaking": False}),
                        _loop
                    )
                threading.Thread(target=_speak_tts, args=(result, _on_done), daemon=True).start()
    except WebSocketDisconnect:
        _listening.clear()
        pass
