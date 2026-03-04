# Frontend Architecture & Integration Guide

Complete documentation of the React/TypeScript UI for the AI Assistant.

## Overview

The frontend is a single-page React application built with:
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 5 (fast development, optimized production builds)
- **Styling:** CSS3 with responsive design
- **Backend Communication:** HTTP (Fetch API) + WebSocket

## Component Structure

### App.tsx (Main Container)

**Purpose:** Orchestrates chat, avatar, and audio playback

**Responsibilities:**
- Manage application state (messages, animation, audio)
- Handle chat message sending and API communication
- Control audio playback and sync animation
- Error handling and loading states

**Key Functions:**
- `handleSendMessage(text)` — Send chat request to backend
- `toggleAudioPlayback()` — Play/pause audio
- Audio sync via `audioStartTime` state

**State Structure:**
```typescript
interface AppState {
  sessionId: string;        // Session ID for chat continuity
  messages: Message[];      // Chat history
  currentAnimation?: AnimationPayload;  // Avatar animation data
  isLoading: boolean;       // Show loading spinner
  error?: string;          // Error messages
  audioUrl?: string;       // Path to WAV file
  isPlaying: boolean;      // Audio playback state
  audioStartTime: number;  // Timestamp when audio started
}
```

### ChatPanel.tsx (Message Display & Input)

**Purpose:** Display message history and handle text input

**Props:**
```typescript
interface ChatPanelProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
}
```

**Features:**
- Auto-scroll to latest message
- Tool results displayed in collapsible details
- Loading indicator with animated dots
- Input disabled while loading
- Timestamp and role display

### AvatarStage.tsx (Avatar Rendering)

**Purpose:** Render animated sprite sheets synchronized with audio

**Props:**
```typescript
interface AvatarStageProps {
  animation?: AnimationPayload;
  audioStartTime?: number;
  isPlaying?: boolean;
}
```

**Animation Flow:**
1. Load sprite image from path in animation payload
2. Parse animation.frames array (contains frame_index, start_time_ms, duration_ms, viseme)
3. Use `requestAnimationFrame` to sync with audio playback
4. Calculate current frame based on elapsed time
5. Draw sprite frame to canvas (handles scaling and centering)

**Canvas Rendering:**
- 2D context for efficient sprite drawing
- Calculates source position in sprite sheet based on frame layout
- Centers sprite while maintaining aspect ratio
- Shows frame debug info in development mode

## Data Flow

### Chat Message Flow

```
User Input
    ↓
ChatPanel input handler
    ↓
App.handleSendMessage()
    ↓
api.chat(ChatRequest)
    ↓
POST /chat → Backend
    ↓
Backend returns ChatResponse with:
  - text: Assistant response
  - tool_results: Tool execution results
  - audio: { artifact_id, wav_path, duration_seconds }
  - avatar: AnimationPayload
    ↓
App updates state:
  - Add message to messages[]
  - Set currentAnimation = response.avatar
  - Set audioUrl = response.audio.wav_path
  - Set isPlaying = true
    ↓
AvatarStage receives animation prop
Audio element src updated
Animation loop begins
```

### Audio-Avatar Sync

```
Audio plays
    ↓
audioRef.onplay event → set audioStartTime = Date.now()
    ↓
requestAnimationFrame loops
    ↓
Calculate elapsed = Date.now() - audioStartTime
    ↓
Find frame where:
  frame.start_time_ms <= elapsed < frame.start_time_ms + frame.duration_ms
    ↓
Draw that frame to canvas
    ↓
When elapsed >= audio_duration_ms:
  Stop animation loop
  Set isPlaying = false
```

## API Integration

### HTTP Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server health check |
| `/tools` | GET | List available tools |
| `/chat` | POST | Send chat request, get response |
| `/audit` | GET | Permission audit log |
| `/events` | GET | Event history |
| `/avatar/sprites` | GET | List available sprites |
| `/avatar/sprite/{name}` | POST | Switch active sprite |
| `/artifacts/*` | GET | Static files (audio, sprites) |

### WebSocket Endpoint

**`/ws/events`** — Real-time event stream

**Message Format:**
```json
{
  "name": "event_name",
  "timestamp": "2026-03-03T12:00:00Z",
  "payload": { ... }
}
```

**Events Monitored:**
- `avatar_speak_start` — Avatar started speaking
- `avatar_speak_end` — Avatar stopped speaking
- Other diagnostic events

Currently events are logged to console for debugging. Could be extended to show real-time status indicators.

## Styling

### Layout

- **Main Grid:** 50/50 split on desktop, stacked on mobile
  - Left: Avatar stage with audio controls
  - Right: Chat panel (messages + input)
- **Responsive Breakpoint:** 768px (tablets and down stack vertically)

### Color Scheme

- **Primary:** Purple gradient (#667eea to #764ba2)
- **Background:** Light gray (#f5f5f5, #f9f9f9)
- **Text:** Dark gray (#333, #666)
- **Accent:** Light purple (#f0f0ff for hover states)

### Animations

- **Message Fade-In:** 0.3s slide-up animation
- **Loading Dots:** Blink animation with cascade timing
- **Button Hover:** Scale and shadow effects
- **Scrollbars:** Custom styling on messages container

## Error Handling

**Backend Errors:**
- HTTP error responses → show error banner
- Dismiss button clears error
- Chat input disabled while error shown

**Network Errors:**
- Fetch failures caught and displayed
- WebSocket disconnect → reconnection not yet implemented (could be added)

**Frontend Errors:**
- Image load failures logged to console
- Canvas errors gracefully handled

## State Management

Simple React hooks approach:

```typescript
const [state, setState] = useState<AppState>({ ... })
```

**No Redux/Context API needed** because:
- Single parent component (App) owns all state
- Children are presentation-only
- Complexity is manageable
- Performance is good (no deep nesting)

## Performance Optimizations

1. **Canvas Rendering:** Efficient 2D drawing, no 3D overhead
2. **requestAnimationFrame:** Synced with browser refresh rate
3. **Image Caching:** Sprite image loaded once, reused
4. **Event Debouncing:** WebSocket messages logged but not rendered
5. **CSS:** Hardware-accelerated transforms (scale, translate)

**Memory Usage:**
- Typical: 10-20MB for React + chat history
- Sprite image: ~50KB each
- Audio (WAV): 30KB-100KB per message

## Extending the UI

### Add New Component

1. Create in `src/components/YourComponent.tsx`
2. Export from component
3. Import and use in `App.tsx`

Example:
```typescript
// src/components/ToolPanel.tsx
export const ToolPanel: React.FC<{ tools: Tool[] }> = ({ tools }) => {
  return <div>...</div>
}

// In App.tsx
import { ToolPanel } from './components/ToolPanel'
// Use: <ToolPanel tools={toolsList} />
```

### Add New Chat Feature

1. Add to `AppState` interface in App.tsx
2. Fetch data in relevant handler
3. Pass to child component
4. Update ChatRequest/ChatResponse in api.ts if needed

Example: Display sentiment analysis
```typescript
// Add to response.avatar or new response.sentiment property
interface ChatResponse {
  sentiment?: { label: string; score: number }
}
```

### Customize Styling

Edit `App.css` for global styles. Components can have inline styles or CSS modules.

## Browser Compatibility

**Supported:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Required APIs:**
- Fetch API
- WebSocket
- Canvas 2D
- Audio element
- RequestAnimationFrame

## Deployment

### Development
```bash
npm run dev  # Vite dev server on port 5173
```

### Production Build
```bash
npm run build  # Output to dist/
npm run preview  # Preview production build locally
```

**Deploy `dist/` to:**
- Static hosting (GitHub Pages, Vercel, Netlify)
- CDN (CloudFlare, S3)
- Web server (Nginx, Apache)

**Ensure backend is accessible at:**
- Same origin (same domain)
- Or configure CORS and VITE_API_URL

## Debugging

**Browser DevTools:**

1. **Console:** Check for errors and logs
2. **Network Tab:** Inspect HTTP requests to backend
3. **WebSocket:** Monitor real-time event stream
4. **Performance:** Check rendering performance (FPS in animations)

**Frontend Logs:**
```typescript
// Currently logs to console:
console.log('Event received:', data)
console.error('Chat error:', error)
console.error('Failed to load sprite:', ...)
```

## Future Enhancements

- Real-time typing indicator
- File upload support
- Message reactions/editing
- Dark mode toggle
- Sprite preview gallery
- Advanced animation controls
- Accessibility improvements (ARIA labels, keyboard nav)
