import requests
import json
import time

print('\n' + '='*70)
print('DIAGNOSING SPANISH VOICE ISSUE')
print('='*70)

# Test 1: Simple English request
print('\n[TEST 1] Simple English Request')
payload_en = {
    'session_id': 'test-en',
    'actor': 'user', 
    'text': 'Hello world',
    'language': 'en',
    'permissions': ['*']
}

try:
    resp = requests.post('http://localhost:8000/chat', json=payload_en, timeout=30)
    data = resp.json()
    voice = data['audio']['voice_id']
    duration = data['audio']['duration_seconds']
    print(f'✓ Voice: {voice}')
    print(f'✓ Duration: {duration}s')
    print(f'✓ Response: {data["text"][:50]}...')
except Exception as e:
    print(f'✗ Error: {e}')

time.sleep(1)

# Test 2: Spanish request
print('\n[TEST 2] Spanish Request')
payload_es = {
    'session_id': 'test-es',
    'actor': 'user',
    'text': 'Hola, ¿cómo estás?',
    'language': 'es',
    'permissions': ['*']
}

try:
    resp = requests.post('http://localhost:8000/chat', json=payload_es, timeout=30)
    data = resp.json()
    voice = data['audio']['voice_id']
    duration = data['audio']['duration_seconds']
    print(f'✓ Voice: {voice}')
    print(f'✓ Duration: {duration}s')
    print(f'✓ Response: {data["text"][:50]}...')
    
    # Check if it's the right voice
    if 'ald' in voice.lower():
        print('✓ CORRECT: Spanish voice selected')
    elif 'amy' in voice.lower():
        print('✗ WRONG: English voice selected for Spanish text!')
    else:
        print(f'? Unknown voice: {voice}')
except Exception as e:
    print(f'✗ Error: {e}')

print('\n' + '='*70)
