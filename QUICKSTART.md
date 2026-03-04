# 🚀 AI Assistant - Quick Start Guide

## One-Step Startup

### Windows
```batch
START_PROJECT.bat
```

Or with PowerShell:
```powershell
.\START_PROJECT.ps1
```

That's it! The system will:
1. ✅ Start Ollama with the LLM model
2. ✅ Start the Backend API
3. ✅ Start the Frontend server
4. ✅ Open the web browser automatically

**Default model**: `llama3.2:3b` (2GB, fast, good quality)

---

## Available Models

You can choose different models based on your needs:

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| `llama3.2:1b` | 1.3GB | ⚡⚡⚡ Very Fast | Basic | Testing, low-end systems |
| `llama3.2:3b` | 2.0GB | ⚡⚡ Fast | Good | **Default, balanced** |
| `llama3:8b` | 4.7GB | ⚡ Medium | Excellent | Best quality, needs 8GB+ RAM |
| `gemma2:9b` | 5.4GB | ⚡ Medium | Excellent | Strong reasoning |
| `phi4:latest` | 9.1GB | ⚡ Medium | Very Good | Instruction-following |
| `qwen2.5:7b` | 4.7GB | ⚡ Medium | Excellent | Multilingual |

### Use a Different Model

```powershell
# Use llama3:8b (better quality)
.\START_PROJECT.ps1 -Model "llama3:8b"

# Use phi4 (instruction-tuned)
.\START_PROJECT.ps1 -Model "phi4:latest"
```

---

## Manual Startup (if needed)

### 1️⃣ Start Ollama

```powershell
.\scripts\start_ollama.ps1 -Model "llama3.2:3b"
# Or use different model:
.\scripts\start_ollama.ps1 -Model "llama3:8b"
```

### 2️⃣ Start Backend

```powershell
cd .\assistant\backend
.\..\..\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3️⃣ Start Frontend

```powershell
cd .\assistant\frontend
$env:Path += ";C:\Program Files\nodejs"
npm run dev
```

---

## Access Points

Once running:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5175 | Chat interface, avatar |
| Backend API | http://localhost:8000 | API endpoints |
| Backend Docs | http://localhost:8000/docs | Interactive API docs |
| Ollama | http://localhost:11434 | LLM API (advanced) |

---

## Configuration

### Environment Variables

Set these before starting to customize behavior:

```powershell
# Use custom Ollama URL
$env:OLLAMA_API_URL = "http://localhost:11434/v1"

# Use different LLM server (e.g., local llama.cpp)
$env:OLLAMA_API_URL = "http://localhost:8000/v1"
```

### Troubleshooting

**"Port 8000 already in use"**
- Change backend port: `python -m uvicorn backend.app:app --port 8001`
- Or kill existing process: `Get-Process python | Stop-Process -Force`

**"Ollama not found"**
- Download from https://ollama.ai
- Install and ensure it's in your PATH
- Run `ollama --version` to verify

**"npm not found"**
- Node.js not installed or not in PATH
- Install from https://nodejs.org
- Or add to PATH: `$env:Path += ";C:\Program Files\nodejs"`

**"Model loading takes forever"**
- First load of a model is slow (downloads needed files)
- Subsequent loads are instant (cached)
- Use a smaller model: `llama3.2:3b` instead of `llama3:8b`

---

## Project Structure

```
AI-Headroom/
├── START_PROJECT.ps1       # Main startup script
├── START_PROJECT.bat       # Windows batch wrapper
├── scripts/
│   └── start_ollama.ps1    # Ollama helper
├── assistant/
│   ├── backend/            # FastAPI backend
│   ├── frontend/           # React frontend
│   └── artifacts/          # Generated audio files
├── .venv/                  # Python environment
└── SETUP_GUIDE.md          # Detailed setup
```

---

## What Happens When You Send a Message

```
User Input (Frontend)
         ↓
REST API Request (Backend)
         ↓
LLM Processing (Ollama)
         ↓
AI Response Generated
         ↓
Text-to-Speech Synthesis (Piper)
         ↓
WAV File Generated
         ↓
Avatar Animation Generated
         ↓
Frontend Updates Display & Plays Audio
```

**Latency**: ~2-10 seconds depending on model and message length.

---

## Prerequisites

- Ollama installed (https://ollama.ai) ✅ Already done
- Python 3.12+ ✅
- Node.js 18+
- 2GB+ RAM (for `llama3.2:3b`), 8GB+ for larger models

## Next Steps

1. ✅ Run `.\START_PROJECT.ps1`
2. ✅ Send a message in the web interface
3. ✅ Listen to the AI response with voice!
4. 🎉 Customize the avatar and functionality as needed

---

## Support

For detailed setup: See `SETUP_GUIDE.md`
For architecture: See `assistant/frontend/ARCHITECTURE.md`
For master plan: See `Jetson_Orin_Local_AI_Assistant_Master_Plan.md`


### Install Dependencies

```bash
cd assistant/backend

# Install Python packages
pip install -r requirements.txt
```

If no requirements.txt exists, install manually:

```bash
pip install fastapi uvicorn pydantic httpx
```

## 2. LLM Setup (Optional but Recommended)

The backend can work with or without a local LLM server.

### Option A: Use llama.cpp

Download and run llama.cpp server:

```bash
# Download llama.cpp (if not already installed)
# From: https://github.com/ggerganov/llama.cpp/releases

# Place a quantized model in models/ directory
# Example: models/mistral-7b-instruct.gguf

# Start llama.cpp server on port 8000
./llama-server -m models/mistral-7b-instruct.gguf \
  --port 8000 \
  --n_gpu_layers 99 \
  --embeddings
```

### Option B: Use Mock LLM (Development)

The backend automatically falls back to a mock LLM if the server is unavailable. Responses will be generic but functional for testing.

## 3. TTS Setup (Optional but Recommended)

The backend can work with or without Piper TTS.

### Install Piper TTS

```bash
# Install Piper (Python package)
pip install piper-tts

# Or install from source:
# https://github.com/rhasspy/piper

# Download voices (optional, uses mock TTS if unavailable)
mkdir -p ./piper/models
# Download models to ./piper/models/
```

The backend automatically falls back to mock WAV generation if Piper is unavailable.

## 4. Start Backend Server

```bash
cd AI-Headroom/assistant/backend

# Activate Python environment (if not already)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# Start FastAPI server
python -m uvicorn app:app --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Test the backend:
```bash
curl http://localhost:8000/health
# Response: {"status":"ok"}
```

## 5. Frontend Setup

### Install Dependencies

```bash
cd AI-Headroom/assistant/frontend

npm install
```

### Start Development Server

```bash
npm run dev
```

You should see:
```
VITE v5.0.0  ready in 123 ms

➜  Local:   http://localhost:5173/
```

Open http://localhost:5173 in your browser.

## 6. Test the System

1. **Send a Chat Message**
   - Type "Hello" in the chat input
   - Click Send
   - Watch the avatar animate while TTS plays
   - See the assistant's response in the chat

2. **Test Tools** (if available)
   - Type "What time is it?" — should execute datetime tool
   - Type "Echo: hello world" — should execute echo tool
   - Check tool results in the message panel

3. **Avatar Animation**
   - Avatar should sync animation frames with audio playback
   - Click the play/pause button to control audio
   - Check browser console for performance metrics

## Troubleshooting

### Backend Connection Issues

**Problem:** Frontend cannot connect to backend
- Check backend is running: `curl http://localhost:8000/health`
- Check `VITE_API_URL` in frontend `.env.local` matches backend URL
- Check firewall allows port 8000

**Problem:** CORS errors in browser console
- Verify backend has CORS middleware configured (app.py)
- Try accessing backend directly: `http://localhost:8000/chat`

### Avatar Not Rendering

**Problem:** Avatar stage shows "No avatar loaded"
- Check backend returns avatar in /chat response
- Verify sprite image path: `/artifacts/sprites/...`
- Check browser console for image load errors
- Ensure artifacts directory exists and is served by backend

**Problem:** Animation doesn't sync with audio
- Check audio playback is working first
- Verify animation timeline has correct duration_ms
- Check browser console for JavaScript errors

### Audio Not Playing

**Problem:** Audio element errors
- Verify WAV file path: `/artifacts/audio/...`
- Check file exists and is accessible
- Try playing WAV directly: `http://localhost:8000/artifacts/audio/...`
- Check browser audio permissions

### LLM / TTS Not Working

**Problem:** "LLM server unavailable" or "Piper not available"
- This is expected if you haven't installed them
- Backend uses mock clients automatically
- Install llama.cpp or Piper for real functionality

## Development Tips

### Frontend Hot Reload

Changes to React components automatically reload in browser (Vite dev server).

### Backend Hot Reload

Run with `--reload` flag for automatic restart on file changes:
```bash
python -m uvicorn app:app --port 8000 --reload
```

### WebSocket Events

Monitor real-time events:
```bash
# Open browser DevTools
# Go to Network tab
# Filter by "WS" 
# Click on "events" WebSocket connection
# Watch messages as you send chat messages
```

### Backend Logs

Check logs for detailed execution flow:

```bash
# Set log level
export LOGLEVEL=DEBUG
python -m uvicorn app:app --port 8000 --log-level debug
```

## Production Deployment

### Building Frontend

```bash
cd assistant/frontend
npm run build
```

Output goes to `dist/` directory. Deploy to any static host (Nginx, GitHub Pages, etc).

**Note:** Frontend still needs backend running on `http://localhost:8000` (or configured URL).

### Jetson Deployment

1. Copy project to Jetson Orin Nano Super 8GB
2. Run setup steps 1-3 above
3. For better performance:
   - Use smaller LLM (e.g., Mistral 7B instead of larger models)
   - Use quantized Piper models
   - Monitor memory usage with `htop`

### Docker (Future)

Dockerfile support coming soon for containerized deployment.

## Next Steps

- **Custom Avatar:** Follow [SPRITE_CUSTOMIZATION.md](SPRITE_CUSTOMIZATION.md) to add Max Headroom sprite
- **Additional Tools:** Implement custom tools in `backend/tools/`
- **Advanced Features:** Add Phase 2 (STT) and enhanced tool capabilities
- **UI Customization:** Modify styles in `frontend/src/App.css`

## Support

Check the README files in each directory:
- `assistant/backend/` - backend architecture
- `assistant/frontend/` - frontend architecture
- [SPRITE_CUSTOMIZATION.md](SPRITE_CUSTOMIZATION.md) - custom avatar guide

## Performance Notes

- **RTX 4070:** Runs all phases smoothly, real-time responses
- **Jetson Orin Nano:** Achieves 2-5 second response times with smaller models
- **Memory:** Average 2-3GB with mock clients, 4-6GB with real LLM/TTS
- **CPU:** Mostly GPU-offloaded, minimal CPU impact

Enjoy your local AI assistant! 🚀
