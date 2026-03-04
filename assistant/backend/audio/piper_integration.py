from __future__ import annotations

import io
import json
import logging
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VoiceInfo:
    language: str
    voice_id: str
    model_path: str


class PiperTTSClient:
    """Real Piper TTS client for local speech synthesis."""

    VOICE_MAP = {
        "en": {
            "voice_id": "en_US-amy-medium",
            "model": "en_US-amy-medium.onnx",
            "language": "en",
        },
        "es": {
            "voice_id": "es_MX-ald-medium",
            "model": "es_MX-ald-medium.onnx",
            "language": "es",
        },
    }

    def __init__(self, voices_dir: str = "./piper/models") -> None:
        self.voices_dir = Path(voices_dir)
        self._available = False
        self._piper = None
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            from piper import PiperVoice
            self._piper_voice_class = PiperVoice
            self._available = True
            logger.info("Piper TTS available")
            # Pre-download models if they don't exist
            self._ensure_models()
        except ImportError:
            logger.warning("Piper TTS not available (pip install piper-tts)")
            self._available = False
    
    def _ensure_models(self) -> None:
        """Auto-download voice models if they don't exist."""
        import urllib.request
        import ssl
        
        # Ignore SSL issues for downloads
        ssl._create_default_https_context = ssl._create_unverified_context
        
        models = {
            "en": {
                "file": "en_US-amy-medium.onnx",
                "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx?download=true"
            },
            "es": {
                "file": "es_MX-ald-medium.onnx",
                "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx?download=true"
            }
        }
        
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        
        for lang, info in models.items():
            model_path = self.voices_dir / info["file"]
            if not model_path.exists():
                try:
                    logger.info(f"Downloading Piper model for {lang}...")
                    urllib.request.urlretrieve(info["url"], str(model_path))
                    logger.info(f"Successfully downloaded {lang} model")
                except Exception as e:
                    logger.warning(f"Could not download {lang} model: {e}")
                    # Don't fail - will use mock TTS instead

    @property
    def available(self) -> bool:
        return self._available

    def synthesize(self, text: str, language: str = "en") -> tuple[bytes, float]:
        """
        Synthesize text to speech using Piper CLI and return (audio_bytes, duration_seconds).
        Returns WAV format audio.
        """
        if not self.available:
            raise RuntimeError("Piper TTS not available. Install: pip install piper-tts")

        selected_lang = "es" if language.lower().startswith("es") else "en"
        voice_info = self.VOICE_MAP[selected_lang]
        model_file = self.voices_dir / voice_info["model"]
        
        # Ensure .onnx extension
        if not str(model_file).endswith(".onnx"):
            model_file = Path(str(model_file) + ".onnx")

        # If requested language model not available, fall back to English voice
        if not model_file.exists():
            if selected_lang != "en":
                logger.warning(f"Piper model not found: {model_file}, falling back to English voice for Spanish text")
                selected_lang = "en"
                voice_info = self.VOICE_MAP["en"]
                model_file = self.voices_dir / voice_info["model"]
                if not str(model_file).endswith(".onnx"):
                    model_file = Path(str(model_file) + ".onnx")
            
            if not model_file.exists():
                logger.error(f"Piper model not found: {model_file}")
                raise FileNotFoundError(f"Piper model not found: {model_file}")

        try:
            import os
            import sys
            
            # Log the exact text being sent to Piper with character details
            logger.info(f"Piper: Synthesizing text: {repr(text[:100])}")  # First 100 chars
            
            # Create temp output file for WAV
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            
            try:
                # Run piper CLI: piper --model model.onnx --output_file output.wav < text
                logger.debug(f"Piper: calling CLI with model {model_file}, text: {text[:50]}...")
                
                # Use python -m piper or explicit path to piper executable
                piper_cmd = [sys.executable, "-m", "piper"]
                
                result = subprocess.run(
                    piper_cmd + [
                        "--model", str(model_file),
                        "--output_file", temp_wav_path
                    ],
                    input=text.encode('utf-8'),
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    stderr = result.stderr.decode('utf-8', errors='ignore')
                    logger.error(f"Piper CLI failed (code {result.returncode}): {stderr}")
                    raise RuntimeError(f"Piper synthesis failed: {stderr}")
                
                # Read the generated WAV file
                if not os.path.exists(temp_wav_path):
                    logger.error(f"Piper did not create output file: {temp_wav_path}")
                    raise RuntimeError("Piper did not generate output file")
                
                with open(temp_wav_path, 'rb') as f:
                    audio_bytes = f.read()
                
                if len(audio_bytes) == 0:
                    logger.error("Piper generated empty audio file")
                    raise RuntimeError("Piper generated empty audio")
                
                file_size_kb = len(audio_bytes) / 1024
                logger.info(f"Piper synthesis success: {file_size_kb:.1f} KB")
                
                # Calculate duration from WAV header
                duration = self._estimate_duration(audio_bytes)
                logger.info(f"Piper TTS synthesized {selected_lang}: {len(text)} chars → {duration:.2f}s audio")
                
                return audio_bytes, duration
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Piper synthesis failed: {type(e).__name__}: {e}")
            raise RuntimeError(f"Piper TTS synthesis failed: {e}")

    def _estimate_duration(self, audio_bytes: bytes) -> float:
        """Estimate audio duration from WAV header."""
        try:
            if len(audio_bytes) < 44:
                logger.warning(f"WAV file too small ({len(audio_bytes)} bytes), cannot read header")
                return 1.0
            
            # WAV format: RIFF header structure
            # Positions:
            # 0-3: "RIFF"
            # 4-7: File size - 8
            # 8-11: "WAVE"
            # 12-15: "fmt "
            # 16-19: Subchunk size (16)
            # 20-21: Audio format (1=PCM)
            # 22-23: Number of channels
            # 24-27: Sample rate
            # 28-31: Byte rate
            # 32-33: Block align
            # 34-35: Bits per sample
            # 36-39: "data"
            # 40-43: Subchunk2 size (audio data size)
            
            sample_rate = struct.unpack("<I", audio_bytes[24:28])[0]
            bits_per_sample = struct.unpack("<H", audio_bytes[34:36])[0]
            channels = struct.unpack("<H", audio_bytes[22:24])[0]
            data_size = struct.unpack("<I", audio_bytes[40:44])[0]
            
            logger.debug(f"WAV header: sample_rate={sample_rate}, bits={bits_per_sample}, channels={channels}, data_size={data_size}")
            
            if sample_rate == 0 or bits_per_sample == 0:
                logger.warning(f"Invalid WAV header values: sample_rate={sample_rate}, bits={bits_per_sample}")
                return 1.0
            
            bytes_per_sample = bits_per_sample // 8
            num_samples = data_size // (channels * bytes_per_sample)
            duration = num_samples / sample_rate
            
            logger.info(f"Calculated audio duration: {duration:.2f}s ({num_samples} samples @ {sample_rate}Hz)")
            return max(0.1, duration)
            
        except Exception as e:
            logger.warning(f"Could not calculate duration from WAV: {e}")
            return 1.0

    def _raw_to_wav(self, raw_audio: bytes, sample_rate: int, channels: int, bits_per_sample: int) -> bytes:
        """Convert raw PCM audio to WAV format."""
        bytes_per_sample = bits_per_sample // 8
        data_size = len(raw_audio)
        
        # WAV file header
        wav_header = bytearray(44)
        # "RIFF" chunk ID
        wav_header[0:4] = b'RIFF'
        # File size - 8
        wav_header[4:8] = struct.pack('<I', 36 + data_size)
        # "WAVE" format
        wav_header[8:12] = b'WAVE'
        # "fmt " subchunk1 ID
        wav_header[12:16] = b'fmt '
        # Subchunk1 size (16 for PCM)
        wav_header[16:20] = struct.pack('<I', 16)
        # Audio format (1 for PCM)
        wav_header[20:22] = struct.pack('<H', 1)
        # Number of channels
        wav_header[22:24] = struct.pack('<H', channels)
        # Sample rate
        wav_header[24:28] = struct.pack('<I', sample_rate)
        # Byte rate
        wav_header[28:32] = struct.pack('<I', sample_rate * channels * bytes_per_sample)
        # Block align
        wav_header[32:34] = struct.pack('<H', channels * bytes_per_sample)
        # Bits per sample
        wav_header[34:36] = struct.pack('<H', bits_per_sample)
        # "data" subchunk2 ID
        wav_header[36:40] = b'data'
        # Subchunk2 size
        wav_header[40:44] = struct.pack('<I', data_size)
        
        return bytes(wav_header) + raw_audio


class MockPiperTTSClient:
    """Mock Piper TTS for testing without Piper installed."""

    VOICE_MAP = {
        "en": {"voice_id": "en_US-amy-medium", "language": "en"},
        "es": {"voice_id": "es_MX-ald-medium", "language": "es"},
    }

    @property
    def available(self) -> bool:
        return True

    def synthesize(self, text: str, language: str = "en") -> tuple[bytes, float]:
        """Generate mock WAV audio (silent) with realistic duration."""
        selected_lang = "es" if language.lower().startswith("es") else "en"
        
        # Estimate duration: ~150 words per minute = ~0.4 seconds per word
        word_count = len(text.split())
        estimated_duration = max(0.5, word_count * 0.4)
        
        wav_bytes = self._generate_wav(
            duration_seconds=estimated_duration,
            sample_rate=22050,
            channels=1,
            bits_per_sample=16,
        )
        
        logger.info(f"Mock TTS synthesized {selected_lang}: {len(text)} chars → {estimated_duration:.2f}s")
        return wav_bytes, estimated_duration

    def _generate_wav(
        self,
        duration_seconds: float,
        sample_rate: int = 22050,
        channels: int = 1,
        bits_per_sample: int = 16,
    ) -> bytes:
        """Generate a WAV file with speech-like audio (sine waves at speech frequencies)."""
        import math
        
        num_samples = int(sample_rate * duration_seconds)
        bytes_per_sample = bits_per_sample // 8
        data_size = num_samples * channels * bytes_per_sample
        
        # WAV header
        header = bytearray(44)
        header[0:4] = b"RIFF"
        header[4:8] = struct.pack("<I", 36 + data_size)
        header[8:12] = b"WAVE"
        header[12:16] = b"fmt "
        header[16:20] = struct.pack("<I", 16)  # fmt chunk size
        header[20:22] = struct.pack("<H", 1)  # PCM format
        header[22:24] = struct.pack("<H", channels)
        header[24:28] = struct.pack("<I", sample_rate)
        header[28:32] = struct.pack("<I", sample_rate * channels * bytes_per_sample)
        header[32:34] = struct.pack("<H", channels * bytes_per_sample)
        header[34:36] = struct.pack("<H", bits_per_sample)
        header[36:40] = b"data"
        header[40:44] = struct.pack("<I", data_size)
        
        # Generate speech-like audio using sine waves at speech frequencies
        # Male voice: 85-155 Hz, Female voice: 165-255 Hz, use blend
        audio_data = bytearray()
        
        # Speech formant frequencies (Hz)
        freq1 = 200  # First formant (vowel color)
        freq2 = 1500  # Second formant
        
        for sample_idx in range(num_samples):
            time = sample_idx / sample_rate
            
            # Vary frequency slightly to add naturalness
            f1 = freq1 + 50 * math.sin(2 * math.pi * 1.5 * time)  # Slowly varying first formant
            f2 = freq2 + 200 * math.sin(2 * math.pi * 2.0 * time)  # Varying second formant
            
            # Combine two sine waves to simulate speech formants
            wave1 = math.sin(2 * math.pi * f1 * time)
            wave2 = 0.5 * math.sin(2 * math.pi * f2 * time)
            combined = (wave1 + wave2) / 2.5  # Blend and normalize
            
            # Add amplitude envelope (speech doesn't start and stop abruptly)
            envelope = min(1.0, time * 5) * min(1.0, (duration_seconds - time) * 10)  # Fade in/out
            
            # Convert to 16-bit signed integer with reduced amplitude to prevent clipping
            sample_float = combined * envelope * 0.6 * 32767
            sample = int(max(-32768, min(32767, sample_float)))
            
            audio_data.extend(struct.pack("<h", sample))
        
        return bytes(header) + bytes(audio_data)


class PiperClientAdapter:
    """Adapter that tries real Piper, falls back to mock."""

    def __init__(self, piper_models_dir: str = "./piper/models") -> None:
        self._primary = PiperTTSClient(voices_dir=piper_models_dir)
        self._fallback = MockPiperTTSClient()

    def synthesize(self, text: str, language: str = "en") -> tuple[bytes, float]:
        """Synthesize to wav bytes and duration."""
        if self._primary.available:
            try:
                return self._primary.synthesize(text=text, language=language)
            except Exception as e:
                logger.warning(f"Primary Piper failed, falling back to mock: {e}")
        return self._fallback.synthesize(text=text, language=language)
