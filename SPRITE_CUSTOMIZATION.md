# Avatar Sprite Customization Guide

This document explains how to add your own custom avatar sprite (like Max Headroom) to the assistant.

## Current Setup

The avatar system uses **sprite sheets** (PNG images containing multiple frames arranged in a grid). The frame layout and viseme mappings are defined in Python code.

**Default sprite:** `retro-character-v1` — a simple 4x4 sprite sheet (16 frames total)

---

## How to Add Your Custom Max Headroom Sprite

### Step 1: Create Your Sprite Sheet

1. **Design your Max Headroom character** using:
   - Piskel (free online): https://www.piskelapp.com/
   - Krita (free desktop): https://krita.org/
   - Aseprite $20 or free alternative

2. **Create a sprite sheet** with the following minimum frames:
   - Frame 0: `neutral` (resting face)
   - Frame 1: `closed` (mouth closed)
   - Frame 2-6: Mouth shapes for visemes (A, E, I, O, U)
   - Frame 7+: Optional (blink, idle, effects)

3. **Export as PNG** with these requirements:
   - All frames same size (e.g., 64x64, 128x128, or 256x256 pixels)
   - Arranged in rows (e.g., 4 frames per row = 4x4 grid)
   - No padding between frames
   - Transparent background (PNG with alpha)

**Example layout (4 frames per row):**
```
Row 0: [neutral] [closed] [A-mouth] [E-mouth]
Row 1: [I-mouth] [O-mouth] [U-mouth] [blink-1]
Row 2: [blink-2] [squint] [idle-1] [idle-2]
Row 3: [unused] [unused] [unused] [unused]
```

### Step 2: Save Sprite to Assets

```
assistant/
└── assets/
    └── sprites/
        ├── retro-character.png (existing)
        └── max-headroom.png (your new sprite)
```

### Step 3: Register Sprite Metadata

Edit `assistant/backend/avatar/sprite_metadata.py` and add a new `SpriteMetadata` entry:

```python
max_headroom = SpriteMetadata(
    name="max-headroom-v1",
    display_name="Max Headroom",
    image_path="./assets/sprites/max-headroom.png",
    frame_width=128,  # Match your sprite's frame size
    frame_height=128,
    frames_per_row=4,  # How many frames per row
    total_frames=12,  # Total frames in your sprite
    viseme_map={
        "A": 2,       # Frame index for A vowel (open mouth)
        "E": 3,       # Frame index for E vowel (wide smile)
        "I": 4,       # Frame index for I vowel (narrow lips)
        "O": 5,       # Frame index for O vowel (round mouth)
        "U": 6,       # Frame index for U vowel (pursed lips)
        "neutral": 0, # Default/resting face
        "closed": 1,  # Closed mouth
        "silence": 0, # Treat as neutral
    },
    blink_frames=[7, 8],  # Frame indices for blink sequence
    idle_frames=[9, 10, 11],  # Loop these during inactivity
    error_frame=0,  # Fallback if viseme not found
    frame_duration_ms=100,  # Time per frame (100ms = 10 fps)
)

# Register it in _register_default_sprites():
def _register_default_sprites(self) -> None:
    # ... existing code ...
    self._sprites["max-headroom-v1"] = max_headroom
```

### Step 4: Set as Active Sprite

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/avatar/sprite/max-headroom-v1
```

**Option B: In Python startup**
```python
sprite_library.set_active("max-headroom-v1")
```

**Option C: React UI**
```jsx
const response = await fetch('/avatar/sprites');
const sprites = await response.json();
// List shows: [retro-character-v1, max-headroom-v1]

// Switch sprite:
await fetch('/avatar/sprite/max-headroom-v1', { method: 'POST' });
```

---

## Viseme-to-Mouth Mapping Guide

The system maps English phonemes to mouth shapes. Choose the best frame for each:

| Viseme | Sound Examples | Mouth Position | Frame ID |
|--------|---|---|---|
| **A** | "cat", "bat", "ape" | Open mouth, jaw down | 2 |
| **E** | "beet", "see", "meet" | Wide smile, teeth showing | 3 |
| **I** | "bit", "sit", "kit" | Narrow, slight smile | 4 |
| **O** | "boat", "coat", "go" | Rounded, open lips | 5 |
| **U** | "boot", "root", "foot" | Pursed lips, small opening | 6 |
| **neutral** | Between speech | Resting, lips relaxed | 0 |
| **closed** | "p", "b", "m" | Closed mouth, no gap | 1 |

---

## Advanced: Creating Max Headroom Glitch Effects

To enhance Max's iconic "glitchy" look:

### Option 1: CSS Overlay in React

```jsx
<canvas ref={canvasRef} style={{
  filter: 'contrast(1.2) saturate(1.3) hue-rotate(10deg)',
  textShadow: '2px 0 #ff00ff, -2px 0 #00ffff',
}} />
```

### Option 2: Shader-Based Scanlines

```glsl
// In WebGL fragment shader
float scanline = sin(uv.y * 200.0) * 0.1;
fragColor.rgb -= scanline;
fragColor.rgb += noise(uv) * 0.05; // digital "glitch"
```

### Option 3: Frame Skipping (Stuttering Animation)

Modify `AvatarStage.tsx` to randomly skip frames:
```typescript
if (Math.random() < 0.05) {
  // 5% chance to skip frame (jitter effect)
  frameIndex = (frameIndex + Math.floor(Math.random() * 2)) % totalFrames;
}
```

---

## Testing Your Sprite

1. **Verify load:**
   ```bash
   curl http://localhost:8000/avatar/sprites
   # Should list: { "sprites": [ {"name": "max-headroom-v1", ...} ] }
   ```

2. **Test animation:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-max",
       "actor": "user",
       "text": "Hello Max Headroom!",
       "language": "en",
       "permissions": []
     }'
   ```

3. **Check avatar payload:**
   - Response should include `avatar.sprite.name` = `"max-headroom-v1"`
   - Check WebSocket `/ws/events` for `avatar_speak_start` event with full animation timeline

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Sprite not loading | Check path: `./assets/sprites/max-headroom.png` is correct and file exists |
| Frame index out of bounds | Verify `total_frames` matches actual frame count |
| Mouth doesn't match speech | Check `viseme_map` frame indices match your sprite layout |
| Blink looks wrong | Adjust `blink_frames` or try consecutive frame pairs |
| Animation too fast/slow | Increase `frame_duration_ms` (slower) or decrease it (faster) |

---

## File Checklist

- [ ] PNG sprite file at `./assets/sprites/max-headroom.png`
- [ ] `SpriteMetadata` defined in `sprite_metadata.py`
- [ ] `viseme_map` covers all phonemes (A, E, I, O, U, neutral, closed)
- [ ] `blink_frames` and `idle_frames` are valid indices
- [ ] Sprite registered in `_register_default_sprites()`
- [ ] Set as active via API or Python code
- [ ] Test API endpoint returns sprite in `/avatar/sprites`

---

## Next Steps

After you have your Max Headroom sprite working:

1. **Advance animation sync:** Integrate real phoneme extraction from TTS (currently uses character-level estimation)
2. **Add expressions:** Map emotions/sentiment to different sprite sets
3. **Blink automation:** Randomized blinking at natural intervals
4. **Lip-sync refinement:** Use Piper's actual phoneme timing if available

Enjoy your glitchy Max-powered assistant!
