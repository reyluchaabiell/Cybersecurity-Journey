# Cloud Identity Security Investigation

**Microsoft Entra ID & Microsoft 365 Logs Analysis Using Splunk SIEM**

## 1. Project Overview

This project demonstrates a **security investigation of a compromised cloud account** using logs from **Microsoft Entra ID** and **Microsoft 365**, analyzed with **Splunk SIEM**.

The goal of the investigation was to **identify attacker activity, reconstruct the attack timeline, and understand what actions were performed after the account was compromised**.

The investigation focused on a compromised user account:

```
allan.smith@finegalo.thm
```

By correlating multiple log sources, it was possible to identify:

* The **first change made by the attacker**
* The **malicious email sent**
* When the **attacker accessed the victim’s response**
* Where the **email response was stored**

This project demonstrates practical **cloud identity incident investigation**, which is a core skill for **SOC Analysts and Cloud Security Analysts**.

---

# 2. Investigation Environment

### Technologies Used

* **Microsoft Entra ID** – identity authentication and audit logs
* **Microsoft 365** – application activity logs (Outlook / Exchange)
* **Splunk SIEM** – log analysis and investigation platform

### Log Sources Investigated

| Log Source               | Purpose                                   |
| ------------------------ | ----------------------------------------- |
| Entra ID Sign-in Logs    | Identify suspicious login attempts        |
| Entra ID Audit Logs      | Detect account changes or persistence     |
| Microsoft 365 Audit Logs | Identify attacker actions in applications |

Each log source reveals **a different part of the attack story**.

---

# 3. Investigation Goal

The investigation aimed to answer these key questions:

1. **What was the first change made by the attacker?**
2. **What phishing email did the attacker send?**
3. **When did the attacker read the victim’s reply?**
4. **Where was the response stored in the mailbox?**

Answering these questions allowed the reconstruction of the **entire attack timeline**.

---

# 4. Step 1 — Identifying the First Suspicious Activity

The investigation started by examining **Entra ID Audit Logs** to identify changes made to the compromised account.

### Splunk Query

```spl
index=scenario sourcetype="azure:aad:audit" targetResources{}.userPrincipalName="allan.smith@finegalo.thm"
| eval initiator=coalesce('initiatedBy.user.userPrincipalName', 'initiatedBy.app.displayName')
| sort - _time
| table _time, initiator, activityDisplayName, result, targetResources{}.userPrincipalName
```

### Key Finding

The **first change performed by the attacker** was:

```
User started security info registration
```

### What This Means

This action indicates the attacker attempted to **register new authentication information** (for example MFA or recovery options).

Attackers often do this to create **persistence**, ensuring they can keep access to the account even if the password is changed.

---

# 5. Step 2 — Investigating Email Activity

Next, Microsoft 365 logs were analyzed to understand what the attacker did **inside the mailbox**.

### Splunk Query

```spl
index="scenario" sourcetype="o365:management:activity" UserId="allan.smith@finegalo.thm"
| sort - _time
| eval sourceIP=coalesce('ClientIP', 'ClientIPAddress')
| table _time, Operation, UserId, sourceIP, Workload, ObjectId
```

### Activity Timeline

| Time     | Operation         |
| -------- | ----------------- |
| 18:18:10 | New-InboxRule     |
| 18:18:46 | Create            |
| 18:19:39 | Send              |
| 18:19:47 | MailItemsAccessed |
| 18:20:09 | MailItemsAccessed |

---

# 6. Step 3 — Inbox Rule Creation

One of the first actions performed by the attacker was:

```
New-InboxRule
```

This indicates the attacker created a **mail rule inside the mailbox**.

### Why Attackers Do This

Inbox rules allow attackers to:

* Automatically **forward emails**
* **Hide specific messages**
* Monitor responses from victims

In this case, the rule targeted messages from a specific sender.

---

# 7. Step 4 — Phishing Email Sent by the Attacker

The investigation then focused on identifying the **email message sent by the attacker**.

### Result

```
URGENT: Approval for new internal VPN Access
```

### Why This Matters

The subject line suggests a **social engineering attack**.

The attacker likely attempted to trick employees into approving **VPN access**, which could allow further unauthorized entry into internal systems.

---

# 8. Step 5 — Attacker Accessed the Response

After sending the email, the attacker accessed mailbox items.

Log events showed:

| Time     | Operation         |
| -------- | ----------------- |
| 18:19:47 | MailItemsAccessed |
| 18:20:09 | MailItemsAccessed |

The event indicates that the attacker **opened the response sent by the victim**.

---

# 9. Step 6 — Where the Response Was Stored

The investigation also identified where the response email was located inside the mailbox.

### Result

```
\Inbox
```

This confirms that the victim's response was delivered to the **Inbox folder**, where the attacker accessed it.

---

# 10. Reconstructed Attack Timeline

The following timeline summarizes the entire incident:

| Time                  | Attacker Action                    |
| --------------------- | ---------------------------------- |
| Initial access        | Attacker gains access to account   |
| Security modification | Registers new security information |
| 18:18:10              | Creates malicious inbox rule       |
| 18:19:39              | Sends phishing email               |
| 18:19:47              | Accesses mailbox content           |
| 18:20:09              | Reads the victim’s response        |

This sequence demonstrates how attackers **abuse legitimate access to perform internal phishing attacks**.

---

# 11. Key Security Lessons

This investigation highlights several important security insights.

### 1. Cloud identities are prime attack targets

Compromising a single identity can give attackers access to **multiple business services**.

### 2. Email is often used for internal phishing

Attackers commonly use compromised accounts to **send trusted-looking emails inside the organization**.

### 3. Log correlation is critical

No single log source shows the full attack.

Security analysts must combine:

* Identity logs
* Audit logs
* Application logs

to reconstruct the attack timeline.

---

# 12. Skills Demonstrated in This Project

This project demonstrates several core cybersecurity investigation skills:

* Cloud identity incident investigation
* Log analysis using Splunk
* Detection of attacker persistence techniques
* Email-based attack investigation
* Building an attack timeline from log data

These skills are commonly used in **SOC (Security Operations Center) environments**.

---

# 13. Conclusion

This investigation successfully reconstructed a cloud identity compromise using **Microsoft Entra ID and Microsoft 365 logs analyzed in Splunk SIEM**.

The attacker:

1. Gained access to a user account
2. Modified security information to maintain access
3. Created an inbox rule
4. Sent a phishing email
5. Monitored and accessed the victim’s response

By correlating multiple log sources, the full attack story became visible.

This project demonstrates how **log analysis and SIEM tools can uncover attacker behavior and help security teams understand and respond to identity-based attacks in cloud environments**.


**IMAGE TIMELINE**

![Attack Timeline1](attack-timeline.png)
