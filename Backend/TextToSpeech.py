import pygame
import random
import asyncio
import edge_tts
import os
import threading
from dotenv import dotenv_values

# LOAD ENV
env_vars = dotenv_values(".env")

# JARVIS-STYLE VOICE (British, refined, commanding)
AssistantVoice = "en-GB-RyanNeural"

# AUDIO PATH
AUDIO_FILE = "Data/speech.mp3"

# INIT MIXER ONLY ONCE
pygame.mixer.init(
    frequency=48000,
    size=-16,
    channels=2,
    buffer=256
)

# RESPONSES
responses = [
    "The rest of the result has been printed to the chat screen, kindly check it out sir.",
    "The rest of the text is now on the chat screen, sir, please check it.",
    "You can see the rest of the text on the chat screen, sir.",
    "The remaining part of the text is now on the chat screen, sir.",
    "Sir, you'll find more text on the chat screen for you to see.",
    "The rest of the answer is now on the chat screen, sir.",
    "Sir, please look at the chat screen, the rest of the answer is there.",
    "You'll find the complete answer on the chat screen, sir.",
    "The next part of the text is on the chat screen, sir.",
    "Sir, please check the chat screen for more information.",
    "There's more text on the chat screen for you, sir.",
    "Sir, take a look at the chat screen for additional text.",
    "You'll find more to read on the chat screen, sir.",
    "Sir, check the chat screen for the rest of the text.",
    "The chat screen has the rest of the text, sir.",
    "There's more to see on the chat screen, sir, please look.",
    "Sir, the chat screen holds the continuation of the text.",
    "You'll find the complete answer on the chat screen, kindly check it out sir.",
    "Please review the chat screen for the rest of the text, sir.",
    "Sir, look at the chat screen for the complete answer."
]

# THREAD LOCK for audio file safety
tts_lock = threading.Lock()

# When running via web server, disable Python TTS (frontend handles speech)
_SPEECH_ENABLED = True

def set_speech_enabled(enabled):
    global _SPEECH_ENABLED
    _SPEECH_ENABLED = enabled

# GENERATE AUDIO
async def TextToAudioFile(text):

    if os.path.exists(AUDIO_FILE):
        try:
            os.remove(AUDIO_FILE)
        except:
            pass

    communicate = edge_tts.Communicate(
        text=text,
        voice=AssistantVoice,

        # JARVIS: measured, smooth, commanding
        rate="+15%",
        pitch="-12Hz",
        volume="+100%"
    )

    await communicate.save(AUDIO_FILE)

# ULTRA FAST TTS
def TTS(text, func=lambda r=None: True):

    try:

        with tts_lock:
            try:
                asyncio.run(TextToAudioFile(text))
            except RuntimeError:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(TextToAudioFile(text))

            # LOAD + PLAY
            pygame.mixer.music.load(AUDIO_FILE)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()

            while pygame.mixer.music.get_busy():

                if func() == False:
                    pygame.mixer.music.stop()
                    break

                clock.tick(120)

        return True

    except Exception as e:
        print(f"Error in TTS: {e}")
        return False

def stop_tts():
    """Stop current TTS playback."""
    try:
        pygame.mixer.music.stop()
    except:
        pass

# SMART SPEECH - speak the full response
def TextToSpeech(text, func=lambda r=None: True):
    if not _SPEECH_ENABLED:
        return

    text = str(text).strip()

    if not text:
        return

    TTS(text, func)

# MAIN
if __name__ == "__main__":

    while True:

        text = input("Enter the text: ")

        if text.lower() in ["exit", "quit"]:
            break

        TextToSpeech(text)

    pygame.mixer.quit()