#!/usr/bin/env python3
"""
Script to download Piper TTS voice models for the AI Assistant.
"""

import os
from pathlib import Path
import urllib.request
import ssl

# Ignore SSL certificate issues
ssl._create_default_https_context = ssl._create_unverified_context

def download_piper_models():
    """Download English and Spanish Piper models."""
    
    models_dir = Path("./piper/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    models = {
        "en_US-amy-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "es_MX-claudia-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claudia/medium/es_MX-claudia-medium.onnx",
    }
    
    for model_name, url in models.items():
        model_path = models_dir / f"{model_name}.onnx"
        
        if model_path.exists():
            print(f"✓ {model_name} already downloaded")
            continue
        
        print(f"Downloading {model_name}...")
        try:
            urllib.request.urlretrieve(url, model_path)
            print(f"✓ Successfully downloaded {model_name}")
        except Exception as e:
            print(f"✗ Failed to download {model_name}: {e}")
            print(f"  Please download manually from: {url}")
    
    print("\nDone! Piper models are ready.")
    print(f"Models location: {models_dir.absolute()}")

if __name__ == "__main__":
    download_piper_models()
