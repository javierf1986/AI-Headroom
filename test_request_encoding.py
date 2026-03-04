import httpx
import json

payload = {
    'session_id': 'request-test',
    'actor': 'user',
    'text': 'Hola, ¿cómo estás?',
    'language': 'es',
    'permissions': ['*']
}

print('=' * 70)
print('TESTING REQUEST ENCODING')
print('=' * 70)
print()

print(f'Request text (repr): {repr(payload["text"])}')
print(f'Request text codepoints: {[hex(ord(c)) for c in payload["text"][:14]]}')
print()

print('Sending request with Spanish text to backend...')
client = httpx.Client()
resp = client.post(
    'http://localhost:8000/chat', 
    json=payload, 
    headers={"Content-Type": "application/json; charset=utf-8"},
    timeout=30
)
print(f'Status: {resp.status_code}')

data = resp.json()
print(f'Voice: {data["audio"]["voice_id"]}')
print(f'Response text (first 50 chars): {repr(data["text"][:50])}')
print()

if data["audio"]["voice_id"] == "es_MX-ald-medium":
    print("✓ Spanish voice correctly selected")
else:
    print(f"✗ Wrong voice selected: {data['audio']['voice_id']}")
