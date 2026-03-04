# AI Assistant Frontend

React/TypeScript frontend for the fully local AI Assistant with real-time chat, avatar animation, and audio playback.

## Features

- **Real-time Chat** — Send messages and receive responses from the AI assistant
- **Avatar Animation** — Watch the avatar speak with synchronized visemes and animation
- **Audio Playback** — Play and control TTS audio with animation sync
- **Event Streaming** — WebSocket connection for real-time events (diagnostics)
- **Tool Results** — Display tool execution results inline with messages
- **Responsive UI** — Works on desktop and mobile browsers

## Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
cd assistant/frontend
npm install
```

### Environment

Copy `.env.example` to `.env.local` and adjust if needed:

```bash
cp .env.example .env.local
```

Default backend API URL is `http://localhost:8000`.

### Development

Start the dev server:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The dev server includes a proxy to the backend API, so `/api/*` requests are forwarded to `http://localhost:8000/*`.

### Build

Create a production build:

```bash
npm run build
```

Preview the build:

```bash
npm run preview
```

## Architecture

### Components

- **App.tsx** — Main application component, orchestrates chat, avatar, and audio
- **ChatPanel.tsx** — Message history and input form
- **AvatarStage.tsx** — Canvas-based sprite animation renderer
- **api.ts** — HTTP and WebSocket client for backend communication

### Data Flow

1. User types and sends a message
2. `App.tsx` sends ChatRequest to `/chat` endpoint
3. Backend returns ChatResponse with:
   - Assistant text response
   - Audio WAV file path (if TTS enabled)
   - Animation payload (if avatar enabled)
4. App displays message, updates avatar animation, plays audio
5. AvatarStage reads animation timeline and renders sprite frames with frame-accurate timing

### Avatar Animation

The AvatarStage component:
- Loads sprite sheet image
- Parses animation timeline from response payload
- Uses `requestAnimationFrame` to sync sprite frames with audio playback time
- Scales sprite to fit canvas while maintaining aspect ratio

## Integration with Backend

Ensure the backend is running on `http://localhost:8000`:

```bash
# From project root
cd assistant/backend
python -m uvicorn app:app --port 8000
```

The frontend expects these backend endpoints:

- `POST /chat` — Send chat request, get response with audio/avatar
- `GET /tools` — List available tools
- `GET /avatar/sprites` — List available sprites
- `POST /avatar/sprite/{name}` — Switch active sprite
- `WS /ws/events` — WebSocket event stream

## Troubleshooting

### "Cannot connect to backend"

- Check that backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify `VITE_API_URL` in `.env.local` matches backend URL

### Avatar not animating

- Check browser console for sprite image load errors
- Verify sprite image path is correct (`/artifacts/sprites/...`)
- Check that backend returns valid animation payload in `/chat` response

### Audio not playing

- Check browser console for audio element errors
- Verify WAV file path is correct (`/artifacts/audio/...`)
- Check browser audio context is not blocked

## Performance Notes

- Sprite rendering uses canvas for efficient 2D graphics
- Animation syncs to actual audio playback time (`audioRef.currentTime`)
- WebSocket event stream is optional and used for diagnostics
- No external model downloads needed (all local)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires support for:
- Fetch API
- WebSocket
- Canvas 2D
- Blob API
