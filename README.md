# Hotel Booking Voice Chat

Voice-first hotel booking demo using AWS Bedrock Nova Sonic for real-time speech-to-speech conversations.

## Quick Start

### 1. AWS Authentication (required first)

```bash
aws login
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**, click **Start Voice Session**, and start talking.

## How it works

The browser captures microphone audio and streams it over WebSocket to the FastAPI backend. Nova Sonic handles speech recognition, conversation, tool-calling, and text-to-speech in a single model. Audio responses are streamed back and played in the browser. The UI shows the conversation transcript in the centre panel and raw Nova Sonic events in the right panel.

## Features

- Real-time speech-to-speech via **AWS Bedrock Nova Sonic 2.0**
- MCP-style tool calling — search hotels, get details, create/cancel bookings
- 25 mock hotels across US cities (in-memory, no database)
- Two-panel UI: conversation transcript + live Nova Sonic event log
- Session toggle: one button starts and stops the full voice session

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.14, Uvicorn |
| Voice AI | AWS Bedrock Nova Sonic 2.0 (`amazon.nova-2-sonic-v1:0`) |

## Testing without a browser

```bash
cd backend
source .venv/bin/activate
python test_sonic.py
```

Streams a WAV file through the full Nova Sonic pipeline and plays the response through local speakers.

## Troubleshooting

| Problem | Fix |
|---|---|
| `AccessDeniedException` | Run `aws login` first |
| WebSocket connection fails | Ensure backend is on port 8000 |
| No audio output | Set headset/speakers as default output in macOS Sound settings |
| Microphone denied | Allow mic permissions in the browser |

Built with [Kiro](https://kiro.dev)
