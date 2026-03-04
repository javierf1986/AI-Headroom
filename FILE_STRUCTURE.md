# Project File Structure

Complete visual reference of all files in the AI Assistant project.

## Directory Tree

```
c:\dev\AI-Headroom\
│
├── Documentation Files (Start Here)
│   ├── STATUS.md                    [PROJECT OVERVIEW - Read this first]
│   ├── QUICKSTART.md               [5-minute setup guide]
│   ├── FRONTEND_SUMMARY.md         [What was built]
│   ├── SPRITE_CUSTOMIZATION.md     [How to create custom avatars]
│   └── Jetson_Orin_Local_AI_Assistant_Master_Plan.md
│
├── Python Environment
│   └── .venv/                      [Virtual environment - auto-created]
│
└── Assistant Application
    │
    ├── backend/                    [FastAPI Server - Port 8000]
    │   ├── app.py                 [Main entry point, all endpoints]
    │   │
    │   ├── core/                  [Core orchestration]
    │   │   ├── orchestrator.py    [Chat flow coordination]
    │   │   ├── event_bus.py       [Pub/sub event system]
    │   │   ├── permissions.py     [Permission enforcement]
    │   │   ├── session_store.py   [Chat history storage]
    │   │   └── schemas.py         [Pydantic data models]
    │   │
    │   ├── llm/                   [LLM Integration]
    │   │   └── llama_cpp_client.py [llama.cpp client + fallback]
    │   │
    │   ├── audio/                 [TTS Integration]
    │   │   ├── tts_worker.py      [TTS orchestration]
    │   │   ├── piper_integration.py [Piper client]
    │   │   └── wav_artifact.py    [WAV file management]
    │   │
    │   ├── tools/                 [Tool System]
    │   │   ├── base.py            [Tool base class]
    │   │   ├── registry.py        [Tool registry]
    │   │   ├── mock_echo_tool.py  [Example tool]
    │   │   └── mock_datetime_tool.py [Example tool]
    │   │
    │   └── avatar/                [Avatar System]
    │       ├── sprite_metadata.py [Sprite definitions]
    │       ├── controller.py      [Animation timeline]
    │       └── service.py         [Avatar orchestration]
    │
    ├── frontend/                  [React Web UI - Port 5173]
    │   ├── Configuration & Setup
    │   │   ├── package.json         [Node.js dependencies]
    │   │   ├── tsconfig.json        [TypeScript config]
    │   │   ├── tsconfig.node.json   [TS config for Vite]
    │   │   ├── vite.config.ts       [Build & dev server config]
    │   │   ├── index.html           [HTML entry point]
    │   │   ├── .env.example         [Environment variables template]
    │   │   └── .gitignore           [Git ignore rules]
    │   │
    │   ├── Documentation
    │   │   ├── README.md            [Frontend setup & troubleshooting]
    │   │   └── ARCHITECTURE.md      [Technical deep-dive]
    │   │
    │   └── src/                     [React source code]
    │       ├── index.tsx            [React DOM render entry]
    │       ├── App.tsx              [Main application component]
    │       ├── App.css              [Global styles]
    │       ├── api.ts               [Backend HTTP/WS client]
    │       │
    │       └── components/          [React components]
    │           ├── ChatPanel.tsx    [Message history + input form]
    │           └── AvatarStage.tsx  [Avatar sprite renderer]
    │
    └── artifacts/                  [Generated Runtime Files]
        ├── audio/                  [Generated WAV files]
        │   └── *.wav               [TTS audio outputs]
        │
        └── sprites/                [Avatar sprite sheets]
            └── retro-character-v1.png [Default placeholder sprite]
```

## File Count Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| Documentation | 6 | Guides and project planning |
| Backend (Python) | 17 | FastAPI server + integrations |
| Frontend (React) | 17 | Web UI + components + config |
| Artifacts | 2 | Generated audio and sprites |
| **TOTAL** | **42** | Complete system |

## Key Files by Role

### For Getting Started
- `STATUS.md` — Project overview and status
- `QUICKSTART.md` — 5-minute setup guide
- `frontend/README.md` — How to run the frontend
- `backend/app.py` — Main API server

### For Understanding Architecture
- `Jetson_Orin_Local_AI_Assistant_Master_Plan.md` — System design
- `frontend/ARCHITECTURE.md` — Frontend structure
- `backend/core/orchestrator.py` — Chat flow
- `backend/app.py` — All endpoint definitions

### For Customization
- `SPRITE_CUSTOMIZATION.md` — Custom avatar guide
- `frontend/src/App.css` — UI styling
- `backend/tools/base.py` — How to add tools
- `backend/avatar/sprite_metadata.py` — Sprite definitions

### For Debugging
- `backend/core/event_bus.py` — Event history
- `backend/core/permissions.py` — Permission audit log
- `frontend/src/api.ts` — HTTP/WS communication
- Browser DevTools Console — Frontend logs

## File Dependencies

```
HTML Entry Point
  └── index.html
      └── src/index.tsx
          └── src/App.tsx
              ├── src/components/ChatPanel.tsx
              ├── src/components/AvatarStage.tsx
              ├── src/api.ts
              │   └── (HTTP/WS to backend)
              └── src/App.css

Backend Entry Point
  └── app.py
      ├── core/orchestrator.py
      │   ├── llm/llama_cpp_client.py
      │   ├── audio/tts_worker.py
      │   ├── tools/registry.py
      │   └── avatar/service.py
      ├── core/event_bus.py
      ├── core/permissions.py
      └── core/session_store.py
```

## 📦 Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Frontend source code | ~15 KB | TypeScript + CSS |
| Backend source code | ~25 KB | Python modules |
| Config files | ~2 KB | JSON/YAML |
| Documentation | ~50 KB | Markdown guides |
| node_modules (after npm install) | ~500 MB | Dev & production deps |
| Python virtualenv | ~200 MB | Python interpreter + packages |
| Artifacts (empty initially) | ~0 KB | Generated at runtime |
| **Total (without node/venv)** | ~92 KB | Actual project code |

## Running the Project

### Backend
```bash
# From project root
cd assistant/backend
python -m uvicorn app:app --port 8000
```

### Frontend
```bash
# From project root
cd assistant/frontend
npm install  # First time only
npm run dev  # Starts at http://localhost:5173
```

### Build Frontend
```bash
cd assistant/frontend
npm run build  # Creates dist/ folder for deployment
```

## What Gets Generated at Runtime

When you run the system:

```
artifacts/
├── audio/
│   ├── {artifact_id}_1.wav   ← Generated by TTS
│   ├── {artifact_id}_2.wav
│   └── ...
└── sprites/
    ├── retro-character-v1.png  ← Default sprite (created on first run)
    └── {custom_sprite}.png      ← Your custom sprites
```

These are served via `GET /artifacts/*` endpoints from the backend.

## Configuration Files

### Backend Configuration
In `app.py`:
```python
llm_url="http://localhost:8000/v1"      # For llama.cpp
tts_models_dir="./piper/models"         # For Piper
artifact_dir="./artifacts"              # For generated files
```

### Frontend Configuration
In `frontend/.env.local`:
```
VITE_API_URL=http://localhost:8000     # Backend URL
# Leave empty to use default (localhost:8000)
```

## Development Tools Required

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build & dev server |
| pip | Latest | Python package manager |
| npm | 10+ | Node package manager |
| Browser | Modern | Frontend UI (Chrome, Firefox, Safari) |

Optional but recommended:
- llama.cpp — Real LLM support
- Piper TTS — Real speech synthesis
- Docker — Containerized deployment
- Git — Version control

## Editing Tips

### Best Editors
- **VS Code** — Recommended, TypeScript & Python support built-in
- **PyCharm** — Excellent for Python backend
- **WebStorm** — Excellent for React frontend

### File Associations
- `.tsx` files → React TypeScript (edit in VS Code)
- `.ts` files → TypeScript (edit in VS Code)
- `.py` files → Python (edit with any editor)
- `.css` files → CSS (can edit in VS Code)
- `.md` files → Markdown (view in VS Code)
- `.json` files → JSON config (edit in VS Code)

## Version Control (Git)

To safely commit your changes:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit with message
git commit -m "Initial import: All phases complete + Frontend UI"

# View status
git status
```

## Backup Strategy

Important directories to backup:
1. `assistant/` — All source code
2. `.venv/` — Virtual environment (optional, can recreate)
3. Documentation `.md` files

Don't backup:
- `node_modules/` — Auto-recreated from package.json
- `dist/` — Generated build artifact
- `artifacts/` — Generated at runtime

Simple backup:
```bash
xcopy "c:\dev\AI-Headroom\assistant" "c:\backup\AI-Headroom-backup" /E
xcopy "c:\dev\AI-Headroom\*.md" "c:\backup\AI-Headroom-backup" /E
```

---

This structure is designed for:
- ✅ Clear separation of concerns (backend/frontend)
- ✅ Easy maintenance and upgrades
- ✅ Simple customization (tools, sprites, styling)
- ✅ Scalability to more complex features
- ✅ Deployment flexibility (local, Jetson, cloud)
