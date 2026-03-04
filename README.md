# AI Headroom

A sophisticated local AI assistant with real-time avatar animation and synchronized audio generation. Features bilingual support (English/Spanish), advanced avatar customization, and optimized performance for edge devices like Jetson Orin.

## 🚀 Features

- **Real-time Avatar Animation**: Synchronized sprite-based animation with audio playback
- **Bilingual Support**: English and Spanish language support with native Text-to-Speech
- **Multiple Avatar Options**: Customizable avatar sprites with configurable animations
- **Audio Synchronization**: Frame-level synchronization between avatar animation and audio duration
- **Responsive UI**: Dynamic avatar scaling that adapts to container size
- **Local LLM Integration**: Support for Ollama and other local language models
- **Edge-Ready**: Optimized for Jetson Orin and similar computing platforms
- **Developer Tools**: Built-in diagnostics, encoding validation, and debug console

## 📋 Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **Node.js 18+** and npm
- **Ollama** (for local LLM support) - Optional but recommended
- **CUDA** (for GPU acceleration on Jetson) - Optional

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/javierf1986/AI-Headroom.git
cd AI-Headroom
```

### 2. Create Python Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
cd assistant
pip install -r backend/requirements.txt
```

### 4. Install Node Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Download Piper TTS Models (Optional)

For local text-to-speech without Edge TTS:

```bash
python tests/download_piper_models.py
```

### 6. Setup Ollama (Recommended)

Install Ollama from [ollama.ai](https://ollama.ai), then pull a model:

```bash
ollama pull mistral  # or any other model
ollama serve
```

## 🚀 Quick Start

### Option 1: Automated Setup (Windows)

```bash
.\START_PROJECT.ps1
```

This script will:
1. Activate the Python virtual environment
2. Start the backend API server (port 8000)
3. Start the frontend dev server (port 5173)

### Option 2: Manual Setup

**Terminal 1 - Backend:**
```bash
cd assistant
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd assistant/frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## 📚 Project Structure

```
AI-Headroom/
├── assistant/                  # Main application code
│   ├── backend/               # FastAPI backend server
│   │   ├── api/              # API route handlers
│   │   ├── audio/            # Audio processing (TTS, effects)
│   │   ├── avatar/           # Avatar animation logic
│   │   ├── core/             # Core models and orchestration
│   │   ├── llm/              # LLM client integrations
│   │   ├── tools/            # Tool implementations
│   │   ├── app.py            # FastAPI application entry
│   │   └── requirements.txt   # Python dependencies
│   ├── frontend/             # React/TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/   # React components
│   │   │   ├── pages/        # Page components
│   │   │   ├── App.tsx       # Root app component
│   │   │   └── api.ts        # API client
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── piper/                # Piper TTS models
│   └── es/                   # Localization files
├── tests/                    # Test files and utilities
├── logs/                     # Application logs
├── scripts/                  # Utility scripts
├── artifacts/               # Generated artifacts
├── docs/                    # Documentation files
└── .venv/                   # Python virtual environment
```

## 🎮 Usage

### Web Interface

Once the servers are running, open http://localhost:5173 to access the web interface.

**Features:**
- Chat with the AI assistant
- Select avatar and preferred language
- Real-time avatar animation with synchronized audio
- Volume control and playback controls
- Developer diagnostics panel (press 'D' key)
- Session management and chat history

### Chat API

Send requests to the backend API:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "actor": "user",
    "text": "Hello, how are you?",
    "language": "en",
    "permissions": ["*"],
    "client_id": "web-client",
    "preferred_sprite": "max"
  }'
```

## ⚙️ Configuration

### Backend Settings

Edit `backend/core/settings.py`:
- LLM model selection and parameters
- TTS provider (Edge TTS, Piper, Ollama)
- Audio processing options
- Port and host configuration

### Frontend Configuration

Edit `frontend/src/api.ts`:
- Backend API base URL
- Default avatar selection
- UI preferences

### Avatar Customization

Avatar configurations are in `assistant/artifacts/sprites/`:
- `max.json` - Max avatar sprite sheet configuration
- `michael.json` - Michael avatar configuration

Edit sprite metadata to customize:
- Frame dimensions
- Animation frame counts
- Sprite image paths

## 🔧 Development

### Building the Frontend

```bash
cd assistant/frontend
npm run build
```

Output: `dist/` directory

### Running Tests

```bash
cd tests
# Check test files for usage instructions
python test_spanish_voice.py
python test_bilingual_final.py
```

### Code Organization

- **Backend**: FastAPI with modular architecture
  - `core/models.py` - Data models
  - `core/orchestrator.py` - Main orchestration logic
  - `audio/` - Audio processing pipeline
  - `avatar/` - Avatar animation system

- **Frontend**: React + TypeScript with Vite
  - Components in `src/components/`
  - Pages in `src/pages/`
  - Styling with CSS modules
  - API client abstraction in `src/api.ts`

## 🐛 Troubleshooting

### Frontend not loading?
- Ensure backend is running: `http://localhost:8000/health`
- Check frontend build: `npm run build`
- Clear browser cache: `Ctrl+Shift+Delete` or `Cmd+Shift+Delete`

### Avatar animation not synchronized?
- Check console logs for timing information
- Verify audio duration is being received from backend
- Review animation frame scaling in `AvatarStage.tsx`

### Audio not playing?
- Check browser audio permissions
- Verify TTS backend is configured correctly
- Check backend logs in `logs/` folder

### Ollama connection issues?
- Ensure Ollama is running: `ollama serve`
- Check Ollama API endpoint in settings
- Verify firewall isn't blocking port 11434

## 📝 Logs and Diagnostics

Application logs are stored in the `logs/` folder:
- `backend_*.log` - Backend server logs
- View and filter logs to debug issues

### Enable Debug Mode

Press **D** key in the web interface to show diagnostics panel with:
- Encoding validation
- Response timing
- Voice state tracking
- Error messages

## 🌐 Supported Languages

- **English** (en-US)
  - TTS: Edge TTS, Piper, Ollama
  - Models available

- **Spanish** (es-MX)
  - TTS: Edge TTS, Piper, Ollama
  - Localized interface

## 📦 Dependencies

### Backend
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **httpx** - HTTP client
- **edge-tts** - Microsoft Edge Text-to-Speech
- **piper-tts** - Open source TTS
- **ollama** - Local LLM integration

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **CSS** - Styling

## 🚀 Deployment

### Docker Support (Future)
Docker support coming soon for easy deployment.

### Jetson Orin Optimization
The application is optimized for Jetson Orin with:
- Efficient sprite rendering
- GPU-acceleration ready
- Low-latency audio processing
- Memory-conscious design

See `Jetson_Orin_Local_AI_Assistant_Master_Plan.md` for detailed Jetson deployment guide.

## 📖 Documentation

Additional documentation available:
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
- [FILE_STRUCTURE.md](FILE_STRUCTURE.md) - Project file structure
- [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) - Component integration overview
- [SPRITE_CUSTOMIZATION.md](SPRITE_CUSTOMIZATION.md) - Avatar sprite customization guide
- [Jetson_Orin_Local_AI_Assistant_Master_Plan.md](Jetson_Orin_Local_AI_Assistant_Master_Plan.md) - Jetson deployment guide
- [FROZEN_CONFIG_VALIDATION.md](FROZEN_CONFIG_VALIDATION.md) - Configuration validation

## 💡 Recent Updates

### v1.0.0 - Avatar & Audio Synchronization
- ✨ Fixed avatar animation/audio synchronization with frame timestamp scaling
- ✨ Implemented responsive avatar layout with dynamic sizing
- ✨ Added collapsible avatar configuration cards
- 🐛 Fixed audio duration mismatch (estimated vs actual)
- 📦 Reorganized project structure (logs/, tests/ folders)

## 🤝 Contributing

Contributions are welcome! Current development is on the `dev` branch.

**Workflow:**
1. Create feature branch from `dev`
2. Implement changes with clear commit messages
3. Test thoroughly
4. Submit PR to `dev`
5. Code review before merge to `main`

## 📄 License

[Add your license information here]

## 👥 Author

Created by Javier F. with ongoing development and optimization.

## 🙏 Acknowledgments

- Microsoft Edge TTS for cloud-based text-to-speech
- Piper TTS for open-source voice synthesis
- Ollama for local LLM inference
- React and Vite communities

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in `logs/` and markdown files
- Review test files for usage examples

---

**Last Updated:** March 4, 2026  
**Version:** 1.0.0  
**Repository:** https://github.com/javierf1986/AI-Headroom
