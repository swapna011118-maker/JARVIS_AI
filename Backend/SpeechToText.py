import os, io, struct, math, wave
from dotenv import dotenv_values
from openai import OpenAI
import pyaudio

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_vars = dotenv_values(os.path.join(base_dir, ".env"))
InputLanguage = env_vars.get("InputLanguage", "en")
GroqAPIKey = env_vars.get("GroqAPIKey")

client = OpenAI(api_key=GroqAPIKey, base_url="https://api.groq.com/openai/v1")
WHISPER_MODEL = "whisper-large-v3-turbo"

# Audio config — 44.1kHz for better quality
RATE = 44100
FRAME_MS = 20
FRAME_SIZE = int(RATE * FRAME_MS / 1000)
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Find the actual mic (not monitor/loopback)
def _find_mic():
    p = pyaudio.PyAudio()
    idx = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            name = info['name'].lower()
            if 'monitor' not in name and 'output' not in name:
                if idx is None or 'input' in name:
                    idx = i
    p.terminate()
    return idx

MIC_DEVICE = _find_mic()

def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query.endswith(('.', '?', '!')):
        new_query += "."
    return new_query.capitalize()

def frames_to_wav(frames):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return buf.getvalue()

def transcribe_wav(wav_bytes):
    try:
        transcript = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=("audio.wav", io.BytesIO(wav_bytes)),
            language="en"
        )
        return transcript.text.strip()
    except Exception as e:
        print(f"Whisper error: {e}")
        return ""

class AudioStream:
    """PyAudio stream with maxed-out energy-based VAD."""

    GAIN = 3.0

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self._stream = None

    def open(self):
        self._stream = self.pa.open(
            format=FORMAT, channels=CHANNELS, rate=RATE,
            input=True, input_device_index=MIC_DEVICE,
            frames_per_buffer=FRAME_SIZE
        )
        return self._measure_noise()

    def close(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
        self.pa.terminate()

    def _apply_gain(self, frame):
        samples = struct.unpack('<' + 'h' * (len(frame) // 2), frame)
        amplified = [max(-32768, min(32767, int(s * self.GAIN))) for s in samples]
        return struct.pack('<' + 'h' * len(amplified), *amplified)

    def _rms(self, frame):
        samples = struct.unpack('<' + 'h' * (len(frame) // 2), frame)
        return math.sqrt(sum(s * s for s in samples) / len(samples))

    def _measure_noise(self):
        levels = []
        for _ in range(20):
            try:
                frame = self._stream.read(FRAME_SIZE, exception_on_overflow=False)
                levels.append(self._rms(self._apply_gain(frame)))
            except:
                continue
        noise_floor = sum(levels) / len(levels) if levels else 100
        self._noise_floor = noise_floor
        self._threshold = max(noise_floor * 1.25, 300)
        return self

    def capture_speech(self, min_speech_frames=2, silence_timeout_frames=18, stop_check=None):
        ring = []
        speech_frames = []
        silence_count = 0
        speaking = False
        speech_confirm = 0

        while True:
            if stop_check and stop_check():
                if speech_frames:
                    break
                return None
            try:
                frame = self._stream.read(FRAME_SIZE, exception_on_overflow=False)
            except:
                break

            boosted = self._apply_gain(frame)
            energy = self._rms(boosted)
            is_speech = energy >= self._threshold

            ring.append(boosted)
            if len(ring) > 10:
                ring.pop(0)

            if is_speech:
                speech_confirm += 1
                if not speaking and speech_confirm >= min_speech_frames:
                    speaking = True
                    speech_frames = list(ring)
                if speaking:
                    speech_frames.append(boosted)
                silence_count = 0
            else:
                speech_confirm = 0
                if speaking:
                    speech_frames.append(boosted)
                    silence_count += 1
                    if silence_count >= silence_timeout_frames:
                        break

        if not speech_frames:
            return None

        return frames_to_wav(speech_frames)

    def has_speech(self, num_frames=2):
        for _ in range(num_frames):
            try:
                frame = self._stream.read(FRAME_SIZE, exception_on_overflow=False)
                boosted = self._apply_gain(frame)
                if self._rms(boosted) >= self._threshold:
                    return True
            except:
                break
        return False
