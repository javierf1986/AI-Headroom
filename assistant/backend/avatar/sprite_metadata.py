from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class VisemeFrame:
    """Maps a phoneme/viseme to a sprite frame index."""
    viseme: str  # 'A', 'E', 'I', 'O', 'U', 'neutral', 'closed', 'smile'
    frame_index: int


@dataclass(slots=True)
class SpriteMetadata:
    """Defines a sprite sheet's structure and animation frames."""
    name: str  # e.g., "retro-character-v1"
    display_name: str  # e.g., "Retro Robot"
    image_path: str  # relative path to PNG sprite sheet
    frame_width: int  # pixels
    frame_height: int
    frames_per_row: int
    total_frames: int
    
    # Viseme mapping: viseme name -> frame index
    viseme_map: dict[str, int]
    
    # Special frame indices
    blink_frames: list[int]  # e.g., [10, 11, 12] for blink animation
    idle_frames: list[int]  # e.g., [0, 1, 2] for idle loop
    error_frame: int  # fallback if viseme not found
    
    # Animation timing (in milliseconds)
    frame_duration_ms: int = 100  # time per frame
    blink_duration_ms: int = 300  # total blink animation time
    
    # Persona / personality definition for LLM behavior
    persona: Optional[str] = None  # e.g., "You are cheerful and informal"
    
    # Audio glitch effects configuration
    glitch_enabled: bool = False  # Enable audio glitches (Max Headroom style)
    glitch_intensity: float = 0.5  # 0.0 to 1.0 scale (controls effect strength)
    glitch_effects: list[str] = None  # e.g., ["stutter", "pitch", "static", "volume"]
    
    # Per-avatar voice preferences
    preferred_voice_en: str = "en-US-AriaNeural"  # English TTS voice for this avatar
    preferred_voice_es: str = "es-MX-DaliaNeural"  # Spanish TTS voice for this avatar
    
    def __post_init__(self):
        # Default glitch effects if enabled but not specified
        if self.glitch_effects is None:
            object.__setattr__(self, 'glitch_effects', [])


class SpriteLibrary:
    """Manages available sprite sheets and their metadata."""
    
    def __init__(self) -> None:
        self._sprites: dict[str, SpriteMetadata] = {}
        self._active_sprite: Optional[str] = None
        self._register_default_sprites()
    
    def _register_default_sprites(self) -> None:
        """Register built-in sprite definitions."""
        # Placeholder: generic retro character with 16 frames
        retro_char = SpriteMetadata(
            name="retro-character-v1",
            display_name="Retro Character",
            image_path="/artifacts/sprites/retro-character-v1.png",
            frame_width=64,
            frame_height=64,
            frames_per_row=4,
            total_frames=16,
            viseme_map={
                "A": 2,      # open mouth (A sound)
                "E": 3,      # smile (E sound)
                "I": 4,      # narrow mouth (I sound)
                "O": 5,      # round mouth (O sound)
                "U": 6,      # pursed lips (U sound)
                "neutral": 0,
                "closed": 1,
                "silence": 0,
            },
            blink_frames=[8, 9],
            idle_frames=[0, 1, 2],
            error_frame=0,
            frame_duration_ms=100,
        )
        self._sprites["retro-character-v1"] = retro_char
        self._active_sprite = "retro-character-v1"
    
    def register_sprite(self, sprite: SpriteMetadata) -> None:
        """Register a new sprite metadata."""
        self._sprites[sprite.name] = sprite
    
    def get_sprite(self, name: Optional[str] = None) -> SpriteMetadata:
        """Get sprite metadata by name, or return active sprite."""
        if name is None:
            name = self._active_sprite
        if not self._active_sprite:
            raise ValueError("No active sprite set")
        if name not in self._sprites:
            raise ValueError(f"Sprite '{name}' not found")
        return self._sprites[name]
    
    def set_active(self, name: str) -> None:
        """Set the active sprite for avatar rendering."""
        if name not in self._sprites:
            raise ValueError(f"Sprite '{name}' not found")
        self._active_sprite = name
    
    def unregister_sprite(self, name: str) -> None:
        """Remove a sprite from the library. Cannot remove built-in sprites."""
        if name == "retro-character-v1":
            raise ValueError("Cannot delete the built-in default sprite")
        if name not in self._sprites:
            raise ValueError(f"Sprite '{name}' not found")
        del self._sprites[name]
        if self._active_sprite == name:
            self._active_sprite = "retro-character-v1"

    def update_sprite(self, name: str, updates: dict) -> SpriteMetadata:
        """Update mutable fields of an existing sprite's metadata."""
        if name not in self._sprites:
            raise ValueError(f"Sprite '{name}' not found")
        existing = self._sprites[name]
        from dataclasses import replace
        updated = replace(existing, **{k: v for k, v in updates.items() if hasattr(existing, k)})
        self._sprites[name] = updated
        return updated

    def list_sprites(self) -> list[dict]:
        """List all available sprites."""
        return [
            {
                "name": sprite.name,
                "display_name": sprite.display_name,
                "image_path": sprite.image_path,
                "frame_width": sprite.frame_width,
                "frame_height": sprite.frame_height,
                "frames_per_row": sprite.frames_per_row,
                "total_frames": sprite.total_frames,
                "persona": sprite.persona or "",
                "glitch_enabled": sprite.glitch_enabled,
                "glitch_intensity": sprite.glitch_intensity,
                "glitch_effects": sprite.glitch_effects or [],
                "preferred_voice_en": sprite.preferred_voice_en,
                "preferred_voice_es": sprite.preferred_voice_es,
            }
            for sprite in self._sprites.values()
        ]
