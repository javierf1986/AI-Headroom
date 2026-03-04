from __future__ import annotations

import logging
from typing import Any

from backend.avatar.controller import AvatarController
from backend.avatar.sprite_metadata import SpriteLibrary

logger = logging.getLogger(__name__)


class AvatarService:
    """High-level avatar animation service."""

    def __init__(self, sprite_library: SpriteLibrary) -> None:
        self._sprite_lib = sprite_library
        self._controller = AvatarController(sprite_library)

    def create_animation(
        self,
        response_text: str,
        audio_duration_seconds: float,
        language: str = "en",
        sprite_name: str | None = None,
    ) -> dict[str, Any]:
        """Create avatar animation payload for a response."""
        
        timeline = self._controller.generate_animation_timeline(
            audio_duration_seconds=audio_duration_seconds,
            text=response_text,
            sprite_name=sprite_name,
        )
        
        sprite = self._sprite_lib.get_sprite(sprite_name)
        
        payload = {
            "mode": "viseme",
            "fallback_mode": "amplitude",
            "sprite": {
                "name": sprite.name,
                "display_name": sprite.display_name,
                "image_path": sprite.image_path,
                "frame_width": sprite.frame_width,
                "frame_height": sprite.frame_height,
                "frames_per_row": sprite.frames_per_row,
                "total_frames": sprite.total_frames,
            },
            "animation": {
                "audio_duration_ms": timeline.audio_duration_ms,
                "frames": [
                    {
                        "frame_index": f.frame_index,
                        "start_time_ms": f.start_time_ms,
                        "duration_ms": f.duration_ms,
                        "viseme": f.viseme,
                    }
                    for f in timeline.frames
                ],
                "idle_frame": timeline.idle_frame,
                "options": {
                    "blink_probability_per_ms": timeline.blink_probability_per_ms,
                    "auto_blink": True,
                },
            },
            "status": "ready",
        }
        
        return payload

    def create_idle_animation(self, sprite_name: str | None = None) -> dict[str, Any]:
        """Create a simple idle animation (static frame) for sprite loading."""
        sprite = self._sprite_lib.get_sprite(sprite_name)
        
        # Use the first idle frame (typically index 0)
        idle_frame_index = sprite.idle_frames[0] if sprite.idle_frames else 0
        
        payload = {
            "mode": "viseme",
            "fallback_mode": "amplitude",
            "sprite": {
                "name": sprite.name,
                "display_name": sprite.display_name,
                "image_path": sprite.image_path,
                "frame_width": sprite.frame_width,
                "frame_height": sprite.frame_height,
                "frames_per_row": sprite.frames_per_row,
                "total_frames": sprite.total_frames,
            },
            "animation": {
                "audio_duration_ms": 0,
                "frames": [],  # No animation frames for idle state
                "idle_frame": idle_frame_index,
                "options": {
                    "blink_probability_per_ms": 0,
                    "auto_blink": False,
                },
            },
            "status": "ready",
        }
        
        return payload

    def list_sprites(self) -> list[dict]:
        """List available sprites for UI selection."""
        return self._sprite_lib.list_sprites()

    def set_active_sprite(self, sprite_name: str) -> None:
        """Change active sprite."""
        self._sprite_lib.set_active(sprite_name)
        logger.info(f"Avatar sprite switched to: {sprite_name}")
