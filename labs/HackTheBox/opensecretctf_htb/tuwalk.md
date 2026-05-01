# HTB OpenSecret Write-up

## Challenge Information

| Category | Difficulty | Platform |
|---|---:|---|
| Web | Very Easy | Hack The Box |

## Challenge Scenario

A simple help desk portal where users can submit support tickets. The application uses JWT tokens for session management, but something seems off about how they're implemented. The objective is to identify the security flaw and retrieve the flag.

---

## Executive Summary

The OpenSecret web challenge contains a critical security misconfiguration where the JWT signing secret is exposed directly in the client-side JavaScript source code. Since JavaScript delivered to the browser can be viewed by any user, the secret is no longer confidential.

During source code review, I discovered that the application generates JWT tokens directly in the browser and stores them in a cookie named `session_token`. The JWT secret key was hardcoded in the page source, allowing anyone to view it without authentication. The exposed value was the challenge flag itself.

**Vulnerability:** Hardcoded JWT Secret in Client-Side JavaScript  
**Impact:** Secret disclosure, token forgery, authentication bypass  
**Root Cause:** JWT signing logic was implemented on the frontend instead of the backend  

---

## Reconnaissance

After starting the challenge instance, I accessed the web application through the provided IP and port.

The application presented a simple help desk support portal where users could submit tickets. At first glance, there was no obvious input vulnerability such as SQL injection, XSS, or file upload abuse.

Since the challenge description specifically mentioned JWT tokens, I focused on inspecting how the session was created and handled.

---

## Source Code Review

I opened the browser page source and reviewed the embedded JavaScript code.

Inside the JavaScript section, I found the following suspicious line:

```js
const SECRET_KEY = "HTB{0p3n_s3cr3ts_ar3_n0t_s3cr3ts}";
