# Setting Up Local LLM for AI Assistant

The system is configured to use llama.cpp HTTP server on port 8000. You have two options:

## Option 1: Ollama (Recommended for Windows)

**Installation:**
1. Download from https://ollama.ai
2. Install and run: `ollama run mistral`

This will start an API server on port 11434. However, you need to configure it for port 8000, or update the backend config.

## Option 2: LM Studio (Easiest GUI)

1. Download from https://lmstudio.ai
2. Install and open
3. Download a model (e.g., "mistral-7b")
4. Click "Start Server" - it will use port 1234 by default
5. Update backend to use `http://localhost:1234/v1` instead of `http://localhost:8000/v1`

## Option 3: Quick Python Mock (For Testing Only)

If you want to test without a real LLM, you can use the mock fallback which is already set up. The issue is that it only says "Mock response to: [your text]" instead of a real response.

## Current Status

- **Piper TTS**: ✅ Now installed (generates real speech)
- **LLM**: ❌ Not running - need to start one of the options above

## Next Steps

1. Install Ollama or LM Studio
2. Start the model server
3. Restart the backend, or update the LLM client URL in `backend/app.py`
4. Send a chat message - you should now get real responses with real speech!
