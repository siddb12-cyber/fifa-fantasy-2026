"""Quick diagnostic — tests Gemini API key with both auth methods."""
import os, urllib.request, urllib.error, json

key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    print("Set GEMINI_API_KEY first"); exit()

key_type = "Bearer (AQ. format)" if key.startswith("AQ.") else "API key (AIza format)"
print(f"Key format detected: {key_type}\n")

def make_req(url, payload, use_bearer=False):
    headers = {"Content-Type": "application/json"}
    if use_bearer:
        headers["Authorization"] = f"Bearer {key}"
    else:
        url = url + f"?key={key}"
    req = urllib.request.Request(url, data=payload, headers=headers)
    return req

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
payload_txt = json.dumps({"contents": [{"parts": [{"text": "Say hi"}]}]}).encode()
payload_img = json.dumps({
    "contents": [{"parts": [{"text": "A red football, cartoon style"}]}],
    "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
}).encode()

models_to_test = [
    ("gemini-2.0-flash", "text", payload_txt),
    ("gemini-2.0-flash-preview-image-generation", "image", payload_img),
    ("gemini-2.0-flash-exp", "image", payload_img),
    ("imagen-3.0-generate-002", "image", payload_img),
]

for use_bearer in [False, True]:
    auth_label = "Bearer header" if use_bearer else "?key= param"
    print(f"=== Auth method: {auth_label} ===")
    for model, kind, payload in models_to_test:
        url = f"{BASE}/{model}:generateContent"
        req = make_req(url, payload, use_bearer)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                resp = json.loads(r.read())
            parts = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            has_img = any("inlineData" in p for p in parts)
            has_txt = any("text" in p for p in parts)
            print(f"  {model}: OK  image={has_img}  text={has_txt}  *** WORKS ***")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:120] if e.fp else ""
            print(f"  {model}: {e.code} {e.reason}  {body}")
        except Exception as e:
            print(f"  {model}: ERROR {e}")
    print()
