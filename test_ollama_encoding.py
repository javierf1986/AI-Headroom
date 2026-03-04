import httpx
import json

payload = {
    'model': 'gemma2:9b',
    'messages': [{'role': 'user', 'content': 'Hola, ¿cómo estás?'}]
}

print("=" * 70)
print("DIAGNOSING OLLAMA ENCODING ISSUE")
print("=" * 70)
print()

print("Sending request to Ollama...")
try:
    client = httpx.Client(timeout=30)
    resp = client.post('http://localhost:11434/v1/chat/completions', json=payload)
    
    print(f"Status: {resp.status_code}")
    print(f"Response charset from header: {resp.headers.get('content-type')}")
    print()
    
    # Try different decodings
    print(f"Raw bytes (first 300): {resp.content[:300]}")
    print()
    
    data = resp.json()
    text = data['choices'][0]['message']['content']
    
    print(f"Text as received (repr): {repr(text)}")
    print()
    print(f"Text printed directly:\n{text}")
    print()
    
    # Check codepoints
    print(f"First 30 codepoints: {[hex(ord(c)) for c in text[:30]]}")
    print()
    
    # Check if it's mojibake
    if 'Θ' in text or 'φ' in text or '┐' in text:
        print("✗ MOJIBAKE DETECTED - Text is corrupted")
    else:
        print("✓ Text appears correct")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
