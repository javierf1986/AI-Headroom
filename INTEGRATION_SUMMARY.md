# AI Assistant - Ollama Integration & Startup Scripts

## What Has Been Implemented

### ✅ Completed Integration Tasks

1. **Ollama Integration**
   - Backend now automatically connects to Ollama API (port 11434)
   - Configurable via `$env:OLLAMA_API_URL` environment variable
   - Falls back to llama.cpp if needed
   - LLM client detects available models automatically

2. **Startup Scripts Created**
   - `START_PROJECT.ps1` - Master startup script (PowerShell)
   - `START_PROJECT.bat` - Windows batch wrapper
   - `scripts/start_ollama.ps1` - Ollama launcher with model loading

3. **Code Improvements**
   - Permission manager now properly handles wildcard `"*"` 
   - Mock LLM responses improved with context awareness
   - Piper TTS models auto-download on first run
   - LLM client auto-detects running models

4. **Documentation**
   - `QUICKSTART.md` - Quick start guide
   - `SETUP_GUIDE.md` - Detailed setup instructions

### 📁 Files Created/Modified

**New Files:**
- `START_PROJECT.ps1` - Master startup orchestrator
- `START_PROJECT.bat` - Batch launcher
- `scripts/start_ollama.ps1` - Ollama service launcher
- `QUICKSTART.md` - Updated quick start guide
- `SETUP_GUIDE.md` - Comprehensive setup documentation
- `download_piper_models.py` - Manual model downloader

**Modified Files:**
- `assistant/backend/app.py` - Added Ollama URL configuration
- `assistant/backend/llm/llama_cpp_client.py` - Improved LLM client with model detection
- `assistant/backend/audio/piper_integration.py` - Enhanced Piper TTS setup

---

## How to Use

### Quick Start

```powershell
cd C:\dev\AI-Headroom
.\START_PROJECT.ps1
```

This will:
1. Start Ollama with `llama3.2:3b` model  
2. Start the Backend API on port 8000
3. Start the Frontend on port 5175
4. Open the web browser automatically

### Custom Model

```powershell
.\START_PROJECT.ps1 -Model "llama3:8b"
```

Available models on your system:
- `llama3.2:1b` - Fastest (1.3GB)
- `llama3.2:3b` - **Default** (2.0GB) 
- `llama3:8b` - Best quality (4.7GB)
- `gemma2:9b` - Strong (5.4GB)
- `phi4:latest` - General purpose (9.1GB)
- `qwen2.5:7b` - Multilingual (4.7GB)

### Manual Steps (if needed)

**Step 1: Start Ollama**
```powershell
.\scripts\start_ollama.ps1 -Model "llama3.2:3b"
```

**Step 2: Start Backend**
```powershell
cd .\assistant
..\\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

**Step 3: Start Frontend (new terminal)**
```powershell
cd .\assistant\frontend  
$env:Path += ";C:\Program Files\nodejs"
npm run dev
```

---

## System Architecture

```
Frontend (React)                  Backend (FastAPI)              LLM (Ollama)
http://localhost:5175   ←→       http://localhost:8000    ←→   http://localhost:11434

     Chat Input
         ↓
   REST /chat request
         ↓
   LLM Processing
         ↓
   AI Response Text
         ↓
   TTS Synthesis (Piper)
         ↓
   Audio WAV File
         ↓
   Avatar Animation
         ↓
   Display & Playback
```

---

## Configuration

### Environment Variables

```powershell
# Use a different Ollama URL
$env:OLLAMA_API_URL = "http://localhost:11434/v1"

# Use local llama.cpp instead
$env:OLLAMA_API_URL = "http://localhost:8000/v1"
```

### Port Configuration

- **Frontend**: 5175 (hardcoded in Vite config)
- **Backend**: 8000 (change with `--port` flag)
- **Ollama**: 11434 (default Ollama port)

---

## Troubleshooting

### "Ollama not responding"
- Verify Ollama is installed: `ollama --version`
- Verify it's running: `ollama list`
- Try: `ollama serve` in a separate terminal

### "Port already in use"
- Find process: `Get-Process -Id lsof | grep :8000`
- Kill it: `Stop-Process -Id [PID] -Force`
- Or use different port: `python -m uvicorn backend.app:app --port 8001`

### "Python module not found"
- Run from `assistant` directory, not `assistant/backend`
- Set `PYTHONPATH`: `$env:PYTHONPATH = "."`

### "Frontend not loading"
- Check Node.js: `node --version` (should be 18+)
- Add to PATH: `$env:Path += ";C:\Program Files\nodejs"`

### "Model download hangs"
- This is normal - first load downloads model files
- `llama3.2:3b` (2GB) takes ~2-5 minutes on first run
- Subsequent loads are instant (cached)

---

## Performance Expectations

### First Run
- Ollama startup: ~5-10 seconds
- Backend startup: ~5 seconds  
- Frontend startup: ~10 seconds
- Piper model download: variable (internet speed)
- Total: 30-60 seconds

### Operations
- LLM response time: 2-10 seconds (depends on model & prompt)
- TTS synthesis: 0.5-2 seconds
- Avatar animation: instant
- Total round-trip: 3-12 seconds

### Memory Usage
- `llama3.2:3b`: 2GB RAM
- `llama3:8b`: 6-8GB RAM
- Piper TTS: ~500MB
- React Frontend: ~100MB

---

## What's Next

1. **Run the startup script**: `.\START_PROJECT.ps1`
2. **Open http://localhost:5175** in your browser
3. **Send a message** - should get real AI response with voice!
4. **Customize** - Modify avatar, add tools, change voices

---

## Technical Details

### Backend Architecture
- **FastAPI**: REST API server
- **LlemaCppClient/LLMClientAdapter**: LLM integration (auto-detects models)
- **TTSWorker**: Text-to-speech via Piper
- **Orchestrator**: Coordinates LLM, TTS, tools, avatar
- **EventBus**: Real-time event streaming to frontend

### Model Format
- Ollama: Uses GGUF quantized models
- Piper: Uses ONNX models for TTS
- Both support CPU inference (GPU optional)

### Language Support
- English (en_US)
- Spanish (es_MX)  
- Extensible to other Piper voices

---

## Reference

- Ollama docs: https://ollama.ai
- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev
- Piper TTS: https://github.com/rhasspy/piper

---

**Status**: Integration complete, ready for deployment  
**Last Updated**: 2026-03-03
