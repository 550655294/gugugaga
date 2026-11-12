import os, sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_KEY = "sk-221bcf53fd154c5798f67de661d63319"
API_URL = "https://api.deepseek.com/v1/chat/completions"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
body = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Say 'hello' in one word."}],
    "max_tokens": 10
}
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

print("Sending request to DeepSeek API...")
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        print(f"Response: {result['choices'][0]['message']['content']}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode('utf-8', 'replace')[:500])
except Exception as e:
    print(f"Error: {e}")
