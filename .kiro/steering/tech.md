---
name: Tech Stack
description: Technologies, frameworks, and build commands
---

# Tech Stack

## Frontend

- **Framework:** Next.js 16.4.0 with React 19.3.0
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS 4
- **Icons:** Lucide React
- **WebSocket:** Native browser WebSocket API

### Frontend Commands

```bash
cd frontend
npm install          # Install dependencies
npm run dev         # Start dev server (http://localhost:3000)
npm run build       # Production build
npm run start       # Start production server
npm run lint        # Run ESLint
```

## Backend

- **Framework:** FastAPI 0.142.2
- **Language:** Python 3.9+ (tested with 3.14)
- **Server:** Uvicorn 0.54.0
- **AI:** AWS Bedrock (Nova Sonic 2.0, Claude 3.5 Sonnet)
- **Audio:** soundfile, scipy, numpy, pyaudio
- **Data:** In-memory repositories (no database)

### Backend Commands

```bash
cd backend
python -m venv .venv              # Create virtual environment
source .venv/bin/activate         # Activate venv (macOS/Linux)
pip install -r requirements.txt   # Install dependencies
python -m uvicorn app.main:app --reload --port 8000  # Run server
python test_sonic.py              # Test Nova Sonic integration
```

## AWS Services

- **AWS Bedrock:** Nova Sonic for speech-to-speech, Claude for system prompts
- **Authentication:** AWS credentials via `aws login` command
- **Region:** us-east-1 (default, configurable)

### AWS Configuration Required

```bash
aws login  # MUST run before starting backend
```

## Audio Format Requirements

- **Input:** PCM, 16kHz, 16-bit, mono, base64 encoded
- **Output:** WAV (converted from PCM), 16kHz, 16-bit, mono, base64 encoded
- **Test File:** `backend/resources/can-t-help-me-mono-16KHz.wav`

## Environment Variables

Backend `.env`:
```
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20250122-v1:0
NOVA_SONIC_MODEL_ID=amazon.nova-2-sonic-v1:0
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Key Dependencies

- `boto3` / `aws-sdk-bedrock-runtime` - AWS Bedrock client
- `fastapi` / `uvicorn` - WebSocket API server
- `soundfile` / `scipy` - Audio processing
- `pydantic` - Data validation
- `python-dotenv` - Environment configuration
