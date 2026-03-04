from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core.text_encoding import normalize_text_encoding
from backend.core.settings import settings
from backend.audio.edge_tts_integration import EdgeTTSClient
from backend.audio.wav_artifact import WAVArtifactManager
from backend.audio.audio_effects import apply_glitch_effects

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TTSResult:
    language: str
    voice_id: str
    audio_path: str
    duration_seconds: float
    artifact_id: str
    debug: dict[str, Any] | None = None

    @property
    def wav_path(self) -> str:
        # Backward compatibility for existing callers
        return self.audio_path


class TTSWorker:
    """TTS orchestration using Microsoft Edge TTS."""

    VOICE_MAP = {
        "en": settings.default_voice_en,
        "es": settings.default_voice_es,
    }

    def __init__(self, piper_models_dir: str = "./piper/models", artifact_dir: str = "./artifacts/audio") -> None:
        self._edge_tts_client = EdgeTTSClient()
        self._artifact_manager = WAVArtifactManager(artifact_dir=artifact_dir)
        logger.info("TTS Worker initialized with Edge TTS integration")

    def _normalize_for_tts(self, text: str) -> str:
        """Normalize mojibake/Unicode text so TTS pronounces it naturally."""
        if not text:
            return ""

        normalized = normalize_text_encoding(text)
        normalized = normalized.replace("íHola", "¡Hola")
        normalized = normalized.replace(" íHola", " ¡Hola")
        normalized = normalized.replace("íhola", "¡hola")
        normalized = normalized.replace(" íhola", " ¡hola")
        normalized = re.sub(r"(^|\s)í(?=[A-Za-zÁÉÍÓÚÑáéíóúñ])", r"\1¡", normalized)
        normalized = re.sub(r"(^|\s)ú(?=[A-Za-zÁÉÍÓÚÑáéíóúñ])", r"\1¿", normalized)

        normalized = re.sub(r"[\U0001F300-\U0001FAFF]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _file_fingerprint(self, file_path: str) -> dict[str, Any]:
        target = Path(file_path)
        if not target.exists():
            return {"exists": False}

        stat = target.stat()
        return {
            "exists": True,
            "file_path": str(target.resolve()),
            "file_size": stat.st_size,
            "file_mtime_ns": stat.st_mtime_ns,
        }

    def synthesize(
        self,
        text: str,
        language: str,
        output_dir: str = "./artifacts/audio",
        voice_id_override: str | None = None,
        sprite_glitch_config: dict | None = None,
    ) -> TTSResult:
        """Synthesize text to speech and save WAV file.
        
        Args:
            text: Text to synthesize
            language: Language code
            output_dir: Output directory
            voice_id_override: Optional voice override
            sprite_glitch_config: Optional dict with {"enabled": bool, "intensity": float, "effects": list[str]}
        """
        requested_language = "es" if language.lower().startswith("es") else "en"
        voice_id = voice_id_override or self.VOICE_MAP[requested_language]
        
        # Edge TTS handles special characters well, so minimal normalization needed
        tts_text = text.strip()
        
        # Remove emojis which TTS can't speak
        tts_text = re.sub(r"[\U0001F300-\U0001FAFF]", "", tts_text)
        tts_text = re.sub(r"\s+", " ", tts_text).strip()

        logger.info(f"Edge TTS: synthesizing {len(tts_text)} chars for {requested_language} with voice {voice_id}")
        
        try:
            audio_bytes, duration_seconds = self._edge_tts_client.synthesize(
                text=tts_text,
                language=requested_language,
                voice_override=voice_id_override,
            )
            
            artifact = self._artifact_manager.save_artifact(
                wav_bytes=audio_bytes,
                language=requested_language,
                voice_id=voice_id,
                duration_seconds=duration_seconds,
                format="mp3",  # Edge TTS outputs MP3
            )

            debug_info: dict[str, Any] = {
                "artifact_file": artifact.file_path,
                "before": self._file_fingerprint(artifact.file_path),
                "glitch_requested": False,
                "glitch_applied": False,
                "glitch_error": None,
                "glitch_effects": [],
                "glitch_intensity": 0.0,
            }
            
            # Apply glitch effects if configured
            if sprite_glitch_config and sprite_glitch_config.get("enabled"):
                intensity = sprite_glitch_config.get("intensity", 0.5)
                effect_types = sprite_glitch_config.get("effects", [])

                debug_info["glitch_requested"] = True
                debug_info["glitch_effects"] = effect_types
                debug_info["glitch_intensity"] = intensity
                
                if effect_types and intensity > 0:
                    logger.info(f"Applying audio glitches: {effect_types} (intensity={intensity})")
                    audio_file_path = artifact.file_path
                    try:
                        apply_glitch_effects(
                            audio_path=audio_file_path,
                            intensity=intensity,
                            effect_types=effect_types,
                            output_path=audio_file_path,  # Overwrite in-place
                        )
                        debug_info["glitch_applied"] = True
                        logger.info(f"Successfully applied glitch effects to {audio_file_path}")
                    except Exception as glitch_error:
                        debug_info["glitch_error"] = str(glitch_error)
                        logger.error(f"Failed to apply glitch effects: {glitch_error}", exc_info=True)
                        # Continue without glitches rather than failing
            else:
                debug_info["glitch_error"] = "disabled-or-missing-config"

            debug_info["after"] = self._file_fingerprint(artifact.file_path)
            
            # Convert file path to HTTP path (forward slashes)
            audio_http_path = f"/artifacts/audio/{artifact.artifact_id}_{requested_language}_{voice_id.replace('-', '_')}.mp3"
            
            return TTSResult(
                language=requested_language,
                voice_id=voice_id,
                audio_path=audio_http_path,
                duration_seconds=artifact.duration_seconds,
                artifact_id=artifact.artifact_id,
                debug=debug_info,
            )
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    def list_voices(self) -> dict[str, list[dict]]:
        return self._edge_tts_client.list_voices()

    def synthesize_demo(self, voice_id: str) -> tuple[bytes, float]:
        """Synthesize a short voice preview sample for the given voice ID."""
        return self._edge_tts_client.synthesize_preview(voice_id)
