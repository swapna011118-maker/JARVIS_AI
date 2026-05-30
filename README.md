# JARVIS AI Assistant

> ⚡ Vibe coded — built entirely through natural language prompts with AI.

A holographic JARVIS-style voice assistant with browser UI, PC/web automation, realtime search, and conversational AI.

## Features

- **Voice & Text Input** — Browser mic (Web Speech API) or server mic, plus text chat
- **Holographic UI** — 3D wireframe torus, particle network, aurora glow, animated hexagons, crosshair overlay
- **PC Automation** — File ops, window management, keyboard/mouse, system control, browser control
- **Realtime Search** — Live answers via Groq + OpenRouter
- **Conversational AI** — Powered by Llama 3.3 70B via Groq
- **Memory** — Remembers user context across sessions

## Prerequisites

- Python 3.10+
- Port 8000 available

## Installation

```bash
# Clone the repo
git clone https://github.com/swapna011118-maker/JARVIS_AI.git
cd JARVIS_AI

# Install dependencies
pip install -r Requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
GroqAPIKey=your_groq_api_key
OpenRouterAPIKey=your_openrouter_api_key
OpenRouterBackupKey=your_openrouter_backup_key
HuggingFaceAPIKey=your_huggingface_api_key
CohereAPIKey=your_cohere_api_key
Username=YourName
Assistantname=Jarvis
InputLanguage=en-IN
UserLocation=Your City
```

Get API keys from:
- **Groq** — https://console.groq.com (primary LLM + search)
- **OpenRouter** — https://openrouter.ai/keys (fallback LLM)
- **Cohere** — https://dashboard.cohere.com/api-keys
- **HuggingFace** — https://huggingface.co/settings/tokens

## Usage

```bash
# Start the server
python3 WebMain.py

# Or directly
python3 Backend/WebServer.py
```

Open **http://localhost:8000** in a browser.

## Voice Modes

- **Browser mic** (default) — uses Web Speech API, click mic icon to listen
- **Server mic** — click `BROWSER` button in header to switch, uses PyAudio

## Commands

Say or type things like:

| Category | Examples |
|----------|----------|
| Weather  | "weather", "weather in London" |
| System   | "shutdown", "restart", "sleep", "lock" |
| Browser  | "go to youtube.com", "new tab", "refresh" |
| Files    | "read file ~/test.txt", "create folder test" |
| Media    | "volume 50", "brightness 70", "screenshot" |
| Process  | "process list", "kill firefox" |
| Search   | "what is the latest news?", "who won the match?" |
| General  | "tell me a joke", "explain quantum computing" |
