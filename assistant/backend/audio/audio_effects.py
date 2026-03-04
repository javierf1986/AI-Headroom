"""Audio effects processor for adding Max Headroom-style glitches to TTS audio."""

from __future__ import annotations

import logging
import random
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import WhiteNoise
from pydub.utils import which

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None

logger = logging.getLogger(__name__)


def _ensure_ffmpeg_available() -> None:
    """Ensure pydub has an ffmpeg binary available."""
    if which("ffmpeg"):
        return

    if imageio_ffmpeg is None:
        raise RuntimeError(
            "ffmpeg is required for audio glitch effects. Install ffmpeg or add imageio-ffmpeg."
        )

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    AudioSegment.converter = ffmpeg_exe
    logger.info("Using bundled ffmpeg from imageio-ffmpeg: %s", ffmpeg_exe)


def apply_glitch_effects(
    audio_path: str | Path,
    intensity: float,
    effect_types: list[str],
    output_path: str | Path | None = None,
) -> str:
    """
    Apply glitch effects to an audio file.
    
    Args:
        audio_path: Path to input MP3 file
        intensity: Effect strength (0.0 = subtle, 1.0 = extreme)
        effect_types: List of effects to apply: ["stutter", "pitch", "static", "volume"]
        output_path: Optional output path (defaults to overwriting input)
    
    Returns:
        Path to processed audio file
    """
    audio_path = Path(audio_path)
    if output_path is None:
        output_path = audio_path
    else:
        output_path = Path(output_path)
    
    if not effect_types:
        logger.info(f"No glitch effects specified, skipping processing")
        return str(audio_path)
    
    # Clamp intensity to valid range
    intensity = max(0.0, min(1.0, intensity))
    
    _ensure_ffmpeg_available()

    audio_format = audio_path.suffix.lstrip(".").lower() or "mp3"

    logger.info(f"Loading audio: {audio_path} ({audio_path.stat().st_size} bytes)")
    decoder_codec = "mp3" if audio_format == "mp3" else None
    audio = AudioSegment.from_file(str(audio_path), format=audio_format, codec=decoder_codec)
    original_duration = len(audio)

    # Apply requested effects in sequence
    if "stutter" in effect_types:
        audio = add_stuttering(audio, intensity)

    if "pitch" in effect_types:
        audio = add_pitch_shifts(audio, intensity)

    if "static" in effect_types:
        audio = add_static_bursts(audio, intensity)

    if "volume" in effect_types:
        audio = add_volume_spikes(audio, intensity)

    # Export processed audio
    audio.export(str(output_path), format=audio_format, bitrate="128k")
    final_duration = len(audio)

    logger.info(
        f"Applied glitches: {', '.join(effect_types)} "
        f"(intensity={intensity:.2f}, duration: {original_duration}ms → {final_duration}ms)"
    )

    return str(output_path)


def add_stuttering(audio: AudioSegment, intensity: float) -> AudioSegment:
    """
    Add random stuttering by repeating small segments.
    
    Intensity mapping:
    - 0.0-0.3: Rare, short stutters
    - 0.3-0.7: Moderate stuttering
    - 0.7-1.0: Heavy, frequent stutters
    """
    if intensity < 0.1:
        return audio
    
    # Calculate stutter parameters from intensity
    stutter_probability = 0.05 + (intensity * 0.25)  # 5% to 30% chance per segment
    min_repeats = 2
    max_repeats = 2 + int(intensity * 4)  # 2 to 6 repeats
    
    # Segment audio into chunks to potentially stutter
    segment_length = 150  # ms per segment
    result = AudioSegment.empty()
    
    for i in range(0, len(audio), segment_length):
        chunk = audio[i:i + segment_length]
        
        # Randomly decide to stutter this chunk
        if random.random() < stutter_probability and len(chunk) >= 50:
            # Extract a stutterable portion (first 50-150ms)
            stutter_len = random.randint(50, min(150, len(chunk)))
            stutter_part = chunk[:stutter_len]
            
            # Repeat the stutter portion
            repeat_count = random.randint(min_repeats, max_repeats)
            for _ in range(repeat_count):
                result += stutter_part
            
            # Add the rest of the chunk
            result += chunk[stutter_len:]
            logger.debug(f"Added stutter at {i}ms: {repeat_count}x repeats of {stutter_len}ms")
        else:
            result += chunk
    
    return result


def add_pitch_shifts(audio: AudioSegment, intensity: float) -> AudioSegment:
    """
    Add random pitch shifts to create robotic/glitchy voice effect.
    
    Intensity mapping:
    - 0.0-0.3: Subtle pitch variations (±2 semitones)
    - 0.3-0.7: Moderate shifts (±5 semitones)
    - 0.7-1.0: Extreme shifts (±8 semitones)
    """
    if intensity < 0.1:
        return audio
    
    # Calculate pitch shift parameters
    shift_probability = 0.1 + (intensity * 0.3)  # 10% to 40% chance
    max_shift_semitones = 2 + (intensity * 6)  # ±2 to ±8 semitones
    
    segment_length = 200  # ms per segment
    result = AudioSegment.empty()
    
    for i in range(0, len(audio), segment_length):
        chunk = audio[i:i + segment_length]
        
        if random.random() < shift_probability and len(chunk) >= 50:
            # Random pitch shift in semitones
            shift = random.uniform(-max_shift_semitones, max_shift_semitones)
            
            # Convert semitones to octaves (12 semitones = 1 octave)
            octaves = shift / 12.0
            
            # Pitch shift: new_sample_rate = old_rate * (2 ^ octaves)
            # Pydub uses frame_rate manipulation
            new_sample_rate = int(chunk.frame_rate * (2.0 ** octaves))
            
            # Apply pitch shift
            pitched = chunk._spawn(chunk.raw_data, overrides={'frame_rate': new_sample_rate})
            # Convert back to original frame rate (changes duration to maintain pitch)
            pitched = pitched.set_frame_rate(audio.frame_rate)
            
            result += pitched
            logger.debug(f"Pitch shifted at {i}ms: {shift:+.1f} semitones")
        else:
            result += chunk
    
    return result


def add_static_bursts(audio: AudioSegment, intensity: float) -> AudioSegment:
    """
    Add random bursts of static/white noise.
    
    Intensity mapping:
    - 0.0-0.3: Rare, quiet static
    - 0.3-0.7: Moderate static bursts
    - 0.7-1.0: Frequent, loud static
    """
    if intensity < 0.1:
        return audio
    
    static_probability = 0.02 + (intensity * 0.15)  # 2% to 17% chance
    static_volume_db = -30 + (intensity * 15)  # -30dB to -15dB
    
    segment_length = 300  # ms per segment
    result = AudioSegment.empty()
    
    for i in range(0, len(audio), segment_length):
        chunk = audio[i:i + segment_length]
        
        if random.random() < static_probability and len(chunk) >= 30:
            # Create a short burst of static
            burst_duration = random.randint(20, 100)  # ms
            static = WhiteNoise().to_audio_segment(duration=burst_duration)
            static = static + static_volume_db  # Adjust volume
            
            # Insert static at random position within chunk
            insert_pos = random.randint(0, max(0, len(chunk) - burst_duration))
            
            # Mix static with audio at insert position
            result += chunk[:insert_pos]
            result += chunk[insert_pos:insert_pos + burst_duration].overlay(static)
            result += chunk[insert_pos + burst_duration:]
            
            logger.debug(f"Added static burst at {i + insert_pos}ms: {burst_duration}ms")
        else:
            result += chunk
    
    return result


def add_volume_spikes(audio: AudioSegment, intensity: float) -> AudioSegment:
    """
    Add random volume spikes and drops for distortion effect.
    
    Intensity mapping:
    - 0.0-0.3: Subtle volume variations (±3dB)
    - 0.3-0.7: Moderate spikes (±8dB)
    - 0.7-1.0: Extreme spikes (±15dB)
    """
    if intensity < 0.1:
        return audio
    
    spike_probability = 0.08 + (intensity * 0.25)  # 8% to 33% chance
    max_db_change = 3 + (intensity * 12)  # ±3dB to ±15dB
    
    segment_length = 250  # ms per segment
    result = AudioSegment.empty()
    
    for i in range(0, len(audio), segment_length):
        chunk = audio[i:i + segment_length]
        
        if random.random() < spike_probability and len(chunk) >= 50:
            # Random volume change
            db_change = random.uniform(-max_db_change, max_db_change)
            chunk = chunk + db_change
            logger.debug(f"Volume spike at {i}ms: {db_change:+.1f}dB")
        
        result += chunk
    
    return result
