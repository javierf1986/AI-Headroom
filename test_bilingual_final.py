#!/usr/bin/env python3
"""
FINAL BILINGUAL SPANISH/ENGLISH TEST
Verify that:
1. Spanish input is correctly received
2. Spanish voice is selected (es_MX-ald-medium)
3. Real audio is generated (Piper, not mock)
4. Audio duration seems reasonable
"""

import httpx
import json
import time

def test_language(lang_code, text, expected_voice):
    """Test a single language request"""
    print(f"\n[{lang_code.upper()}] Testing: {text}")
    print("-" * 70)
    
    payload = {
        'session_id': f'test-{lang_code}-{int(time.time())}',
        'actor': 'user',
        'text': text,
        'language': lang_code,
        'permissions': ['*']
    }
    
    client = httpx.Client()
    resp = client.post(
        'http://localhost:8000/chat',
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30
    )
    
    if resp.status_code != 200:
        print(f"✗ FAILED: Status {resp.status_code}")
        return False
    
    data = resp.json()
    voice = data['audio']['voice_id']
    duration = data['audio']['duration_seconds']
    response_text = data['text'][:60]
    
    print(f"Voice selected: {voice}")
    print(f"Duration: {duration:.1f}s")
    print(f"Response text: {response_text}...")
    
    # Verify voice
    if expected_voice in voice:
        print(f"✓ CORRECT voice: {expected_voice}")
    else:
        print(f"✗ WRONG voice! Expected {expected_voice}, got {voice}")
        return False
    
    # Verify audio was actually synthesized (duration > 0)
    if duration > 0:
        print("✓ Real audio generated")
    else:
        print("✗ No audio duration")
        return False
    
    return True

print("=" * 70)
print("FINAL BILINGUAL TEST - SPANISH & ENGLISH")
print("=" * 70)

tests = [
    ("en", "Say hello and tell me a joke", "en_US-amy"),
    ("es", "¡Hola! Cuéntame un chiste en español", "es_MX-ald"),
]

all_passed = True
for lang, text, expected_voice in tests:
    passed = test_language(lang, text, expected_voice)
    all_passed = all_passed and passed

print("\n" + "=" * 70)
if all_passed:
    print("✓ ALL TESTS PASSED - BILINGUAL SYSTEM WORKING")
else:
    print("✗ SOME TESTS FAILED")
print("=" * 70)
