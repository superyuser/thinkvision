import requests
import json

url = "https://api.fireworks.ai/inference/v1/chat/completions"

def get_payload(text: str):
    payload = {
    "model": "accounts/sentientfoundation/models/dobby-mini-unhinged-llama-3-1-8b",
    "max_tokens": 16384,
    "top_p": 1,
    "top_k": 40,
    "presence_penalty": 0,
    "frequency_penalty": 0,
    "temperature": 0.6,
    "messages": [
        {
        "role": "user",
        "content": text
        }
    ]
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer <API_KEY>"
    }
    return requests.request("POST", url, headers=headers, data=json.dumps(payload))