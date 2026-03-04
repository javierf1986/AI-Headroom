# AI Assistant Setup Guide - Getting Real Responses

## Current Status

✅ **Working**: Text-to-speech (using Piper TTS with auto-download)  
✅ **Working**: Mock LLM responses (basic conversations)  
❌ **Needed**: Real LLM server (for actual AI responses)

## The Problem

You're seeing:
- **White noise audio** ← This is being fixed (Piper models auto-downloading)
- **"Mock response to..." messages** ← This is the fallback when no LLM server is running

## Solution: Install a Local LLM

### Option 1: Ollama (Recommended - Easiest)

**Ollama** is a lightweight tool that runs LLMs locally.

1. **Download & Install Ollama**
   - Windows: https://ollama.ai/download
   - Click "Download for Windows"
   - Run the installer

2. **Run a Model**
   ```powershell
   ollama run mistral
   ```
   Or:
   ```powershell
   ollama run neural-chat  # Smaller, faster
   ```

3. **Verify it's working**
   ```powershell
   curl http://localhost:11434/api/tags
   ```

4. **Configure the backend to use Ollama**
   
   Edit `assistant/backend/app.py`, change line 44:
   ```python
   # From:
   llm_client = LLMClientAdapter(llama_cpp_url="http://localhost:8000/v1")
   
   # To:
   llm_client = LLMClientAdapter(llama_cpp_url="http://localhost:11434/v1")
   ```
   
   Note: This requires Ollama to be compatible with OpenAI API endpoints

### Option 2: LM Studio (GUI-Based)

1. Download from https://lmstudio.ai
2. Install and run
3. Search for and download a model (e.g., "mistral-7b-instruct")
4. Click "Start Server"
5. The server will run on port 1234
6. Update backend config to use `http://localhost:1234/v1`

### Option 3: llama.cpp (Manual Setup)

1. Download from https://github.com/ggerganov/llama.cpp
2. Download a quantized GGUF model
3. Run the HTTP server:
   ```bash
   ./server -m model.gguf -ngl 35
   ```

## For Text-to-Speech (Piper)

The system will:
1. **Automatically download** English and Spanish voice models
2. Fall back to **mock speech** if downloads fail
3. Synthesize speech from the LLM responses

If you want to manually download models:
```bash
python download_piper_models.py
```

## Complete Setup Example (Ollama)

```powershell
# 1. Download and install Ollama (one-time)
# From https://ollama.ai/download

# 2. Start Ollama with a model
ollama run mistral

# 3. In another terminal, start the backend
cd C:\dev\AI-Headroom\assistant\backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 4. In another terminal, start the frontend
cd C:\dev\AI-Headroom\assistant\frontend
npm run dev

# 5. Open http://localhost:5175 in your browser
# 6. Send a message - you should now get real AI responses!
```

## Troubleshooting

**Still getting "Mock response to: ..." ?**
- Verify your LLM server is running: `curl http://localhost:8000/v1/models`
- Check the backend logs for connection errors
- Update the LLM URL in `backend/app.py` if needed

**Still getting white noise instead of speech?**
- Wait a moment - Piper models are downloading (~15-30MB total)
- Check terminal logs for "Downloaded" message
- Models will cache after first download

**Frontend shows errors?**
- Make sure backend is running on http://localhost:8000
- Check CORS settings if accessing from different port
- Backend logs: Watch the terminal where backend is running

## Model Recommendations

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| neural-chat | 4B | Very Fast | Good | Fast responses, low memory |
| mistral | 7B | Fast | Excellent | Good balance |
| llama2 | 7B | Fast | Excellent | Great conversations |
| dolphin | 7B-13B | Medium | Excellent | Creative tasks |

## Backend Architecture

```
Frontend (React) → Backend (FastAPI) → LLM Server (Ollama/LM Studio)
    ↓                    ↓                   
HTML/CSS/JS         Python APIs         Language Model
                    
        ↓ Voice ↓
      Piper TTS (Synthesizes speech from text)
```

---

**Need Help?** Check the master plan: `Jetson_Orin_Local_AI_Assistant_Master_Plan.md`
