import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
model = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-90b-vision-instruct")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Clean the URL
if base_url.endswith("/chat/completions"):
    base_url = base_url[:-17]
elif base_url.endswith("/chat/completions/"):
    base_url = base_url[:-18]

invoke_url = f"{base_url.rstrip('/')}/chat/completions"

print(f"Using invoke_url: {invoke_url}")
print(f"Using model: {model}")
print(f"Using key starting with: {api_key[:10] if api_key else 'None'}...")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "Hello! Reply with 'OK' if you can read this."
        }
    ],
    "max_tokens": 10,
    "temperature": 0.2
}

try:
    print("Sending request...")
    response = httpx.post(invoke_url, headers=headers, json=payload, timeout=15.0)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
