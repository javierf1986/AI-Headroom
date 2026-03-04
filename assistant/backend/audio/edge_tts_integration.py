"""Edge TTS integration for high-quality text-to-speech synthesis."""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Tuple

import edge_tts

logger = logging.getLogger(__name__)

# Default voice per language code (used when no explicit voice is selected)
VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "es": "es-MX-DaliaNeural",
    "es-MX": "es-MX-DaliaNeural",
    "es-ES": "es-ES-ElviraNeural",
}

# Full catalog with display name, gender and locale metadata
VOICE_CATALOG: dict[str, list[dict]] = {
    "en": [
        # Female — en-US
        {"id": "en-US-AriaNeural",            "display": "Aria",       "gender": "female", "locale": "en-US"},
        {"id": "en-US-AvaNeural",             "display": "Ava",        "gender": "female", "locale": "en-US"},
        {"id": "en-US-EmmaNeural",            "display": "Emma",       "gender": "female", "locale": "en-US"},
        {"id": "en-US-JennyNeural",           "display": "Jenny",      "gender": "female", "locale": "en-US"},
        {"id": "en-US-MichelleNeural",        "display": "Michelle",   "gender": "female", "locale": "en-US"},
        {"id": "en-US-AnaNeural",             "display": "Ana",        "gender": "female", "locale": "en-US"},
        # Male — en-US
        {"id": "en-US-AndrewNeural",          "display": "Andrew",     "gender": "male",   "locale": "en-US"},
        {"id": "en-US-BrianNeural",           "display": "Brian",      "gender": "male",   "locale": "en-US"},
        {"id": "en-US-ChristopherNeural",     "display": "Christopher","gender": "male",   "locale": "en-US"},
        {"id": "en-US-EricNeural",            "display": "Eric",       "gender": "male",   "locale": "en-US"},
        {"id": "en-US-GuyNeural",             "display": "Guy",        "gender": "male",   "locale": "en-US"},
        {"id": "en-US-RogerNeural",           "display": "Roger",      "gender": "male",   "locale": "en-US"},
        {"id": "en-US-SteffanNeural",         "display": "Steffan",    "gender": "male",   "locale": "en-US"},
    ],
    "es": [
        # es-MX (only 2 exist)
        {"id": "es-MX-DaliaNeural",           "display": "Dalia",      "gender": "female", "locale": "es-MX"},
        {"id": "es-MX-JorgeNeural",           "display": "Jorge",      "gender": "male",   "locale": "es-MX"},
        # es-US (bilingual-friendly)
        {"id": "es-US-PalomaNeural",          "display": "Paloma",     "gender": "female", "locale": "es-US"},
        {"id": "es-US-AlonsoNeural",          "display": "Alonso",     "gender": "male",   "locale": "es-US"},
        # es-ES (Spain)
        {"id": "es-ES-ElviraNeural",          "display": "Elvira",     "gender": "female", "locale": "es-ES"},
        {"id": "es-ES-XimenaNeural",          "display": "Ximena",     "gender": "female", "locale": "es-ES"},
        {"id": "es-ES-AlvaroNeural",          "display": "\u00c1lvaro","gender": "male",   "locale": "es-ES"},
        # es-AR (Argentine)
        {"id": "es-AR-ElenaNeural",           "display": "Elena",      "gender": "female", "locale": "es-AR"},
        {"id": "es-AR-TomasNeural",           "display": "Tom\u00e1s", "gender": "male",   "locale": "es-AR"},
        # es-CO (Colombia)
        {"id": "es-CO-SalomeNeural",          "display": "Salome",     "gender": "female", "locale": "es-CO"},
        {"id": "es-CO-GonzaloNeural",         "display": "Gonzalo",    "gender": "male",   "locale": "es-CO"},
    ],
}


class EdgeTTSClient:
    """Client for Microsoft Edge TTS service."""

    def __init__(self):
        """Initialize Edge TTS client."""
        self.available = True
        logger.info("Edge TTS client initialized - no authentication required")

    async def _synthesize_async(self, text: str, voice: str, output_path: Path) -> None:
        """Async method to synthesize speech using Edge TTS.
        
        Args:
            text: Text to synthesize
            voice: Voice ID (e.g., "en-US-AriaNeural")
            output_path: Path to save WAV file
        """
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))

    def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_override: str | None = None,
    ) -> Tuple[bytes, float]:
        """Synthesize speech from text using Edge TTS.
        
        Args:
            text: Text to convert to speech
            language: Language code (en, es, es-MX, es-ES)
            
        Returns:
            Tuple of (audio_bytes, duration_seconds) - audio is in MP3 format
            
        Raises:
            RuntimeError: If synthesis fails
        """
        # Get voice for language or explicit override
        voice = voice_override or VOICE_MAP.get(language, VOICE_MAP["en"])
        
        # Create temp file for MP3 output
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False, prefix="edge_tts_"
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        try:
            logger.info(f"Edge TTS: synthesizing {len(text)} chars in {language} using voice {voice}")
            
            # Run async synthesis - handle running event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, use asyncio.run()
                asyncio.run(self._synthesize_async(text, voice, temp_path))
            else:
                # Event loop is running, create a new thread
                import threading
                
                def run_in_thread():
                    # Create new event loop in thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self._synthesize_async(text, voice, temp_path))
                    finally:
                        loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=30)
                
                if thread.is_alive():
                    raise RuntimeError("Edge TTS synthesis timed out after 30s")
            
            if not temp_path.exists():
                raise RuntimeError(f"Edge TTS failed to create audio file at {temp_path}")
            
            # Read MP3 bytes (no conversion needed - browsers support MP3)
            mp3_bytes = temp_path.read_bytes()
            
            # Estimate duration from file size (rough approximation: ~1 second per 16KB at 128kbps)
            # This is a rough estimate - actual duration varies by bitrate
            estimated_duration = len(mp3_bytes) / 16000.0
            
            # Clean up temp file immediately after reading
            temp_path.unlink()
            
            logger.info(f"Edge TTS: generated {len(mp3_bytes)} MP3 bytes, estimated duration={estimated_duration:.2f}s")
            
            return mp3_bytes, estimated_duration
            
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}", exc_info=True)
            raise RuntimeError(f"Edge TTS synthesis failed: {e}") from e
        finally:
            # Clean up temp MP3 file if it still exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")

    def get_voice_id(self, language: str) -> str:
        """Get the voice ID for a given language."""
        return VOICE_MAP.get(language, VOICE_MAP["en"])

    def list_voices(self) -> dict[str, list[dict]]:
        """List all supported voices with metadata by language."""
        return VOICE_CATALOG

    def synthesize_preview(self, voice_id: str) -> Tuple[bytes, float]:
        """Synthesize a short preview sentence for the given voice."""
        _PREVIEW_TEXT = {
            "en": "Hello! I'm your AI assistant, ready to help you today.",
            "es": "\u00a1Hola! Soy tu asistente de inteligencia artificial. \u00bfEn qu\u00e9 puedo ayudarte?",
        }
        lang = "es" if voice_id.startswith("es-") else "en"
        text = _PREVIEW_TEXT[lang]
        return self.synthesize(text=text, language=lang, voice_override=voice_id)
