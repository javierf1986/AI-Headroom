from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WAVArtifact:
    artifact_id: str
    file_path: str
    language: str
    voice_id: str
    duration_seconds: float
    sample_rate: int = 22050
    channels: int = 1


class WAVArtifactManager:
    """Manages WAV file artifacts for TTS output."""

    def __init__(self, artifact_dir: str = "./artifacts/audio") -> None:
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"WAV artifact directory: {self.artifact_dir}")

    def save_artifact(
        self,
        wav_bytes: bytes,
        language: str,
        voice_id: str,
        duration_seconds: float,
        format: str = "wav",
    ) -> WAVArtifact:
        """Save audio bytes to file and return artifact metadata.
        
        Args:
            wav_bytes: Audio bytes (WAV or MP3 format)
            language: Language code
            voice_id: Voice identifier
            duration_seconds: Audio duration in seconds
            format: Audio format extension (wav or mp3)
        """
        artifact_id = str(uuid.uuid4())[:8]
        file_name = f"{artifact_id}_{language}_{voice_id.replace('-', '_')}.{format}"
        file_path = self.artifact_dir / file_name
        
        try:
            file_path.write_bytes(wav_bytes)
            logger.info(f"Saved {format.upper()} artifact: {file_path} ({len(wav_bytes)} bytes, {duration_seconds:.2f}s)")
            
            artifact = WAVArtifact(
                artifact_id=artifact_id,
                file_path=str(file_path),
                language=language,
                voice_id=voice_id,
                duration_seconds=duration_seconds,
            )
            return artifact
        except Exception as e:
            logger.error(f"Failed to save {format.upper()} artifact: {e}")
            raise
