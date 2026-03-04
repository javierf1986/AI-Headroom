from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.avatar.sprite_metadata import SpriteLibrary, SpriteMetadata

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VisemeFrame:
    """A single frame in the viseme timeline."""
    frame_index: int
    start_time_ms: float
    duration_ms: float
    viseme: str


@dataclass(slots=True)
class AvatarAnimation:
    """Complete animation timeline for an avatar response."""
    audio_duration_ms: float
    sprite_name: str
    frames: list[VisemeFrame]
    idle_frame: int = 0
    blink_probability_per_ms: float = 0.01  # triggers blink ~every 10 seconds


class AvatarController:
    """Converts TTS audio timing to sprite animation frames."""

    def __init__(self, sprite_library: SpriteLibrary) -> None:
        self._sprite_lib = sprite_library

    def generate_animation_timeline(
        self,
        audio_duration_seconds: float,
        text: str,
        sprite_name: str | None = None,
    ) -> AvatarAnimation:
        """
        Generate sprite frame timeline synchronized to audio duration.
        
        For now, uses a simple viseme estimation based on text.
        In production, would integrate with actual phoneme extraction from TTS.
        """
        sprite = self._sprite_lib.get_sprite(sprite_name)
        audio_duration_ms = audio_duration_seconds * 1000
        
        # Estimate phoneme sequence from text (simplified)
        visemes = self._estimate_visemes(text)
        
        # Distribute visemes across audio duration
        frames = self._create_frame_timeline(visemes, audio_duration_ms, sprite)
        
        logger.info(
            f"Generated animation: {len(frames)} frames over {audio_duration_ms:.0f}ms "
            f"for sprite '{sprite.name}'"
        )
        
        return AvatarAnimation(
            audio_duration_ms=audio_duration_ms,
            sprite_name=sprite.name,
            frames=frames,
            idle_frame=sprite.idle_frames[0] if sprite.idle_frames else 0,
        )

    def _estimate_visemes(self, text: str) -> list[str]:
        """Estimate phoneme sequence from text (very simplified)."""
        viseme_map = {
            'a': 'A', 'e': 'E', 'i': 'I', 'o': 'O', 'u': 'U',
            'y': 'I',
        }
        
        visemes = []
        for char in text.lower():
            if char in viseme_map:
                visemes.append(viseme_map[char])
            elif char == ' ':
                visemes.append('neutral')
        
        if not visemes:
            visemes = ['neutral']
        
        return visemes

    def _create_frame_timeline(
        self,
        visemes: list[str],
        audio_duration_ms: float,
        sprite: SpriteMetadata,
    ) -> list[VisemeFrame]:
        """Create a timeline of sprite frames from visemes."""
        if not visemes:
            return []
        
        # Distribute visemes evenly across audio duration
        duration_per_viseme = audio_duration_ms / len(visemes)
        
        frames = []
        current_time_ms = 0
        
        for viseme in visemes:
            frame_idx = sprite.viseme_map.get(viseme, sprite.error_frame)
            
            frames.append(
                VisemeFrame(
                    frame_index=frame_idx,
                    start_time_ms=current_time_ms,
                    duration_ms=duration_per_viseme,
                    viseme=viseme,
                )
            )
            current_time_ms += duration_per_viseme
        
        return frames
