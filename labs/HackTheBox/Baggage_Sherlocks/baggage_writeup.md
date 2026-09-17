# Sherlocks: Baggage

**Difficulty:** Very Easy\
**Category:** DFIR

<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/10745cc6-53c2-4518-83c3-ac2a7282cac0" />


## Lesson Learned

-   How to use Eric Zimmerman's ShellBags Explorer.
-   Understand how Shellbags work in the Windows Registry.
-   Identify tools brought by an attacker to search for sensitive data.
-   Trace data access, staging, and potential exfiltration activity.

## Sherlock Scenario

This Sherlock provides an opportunity to analyze Shellbag artifacts.
Shellbags can provide evidence of folder access by a specific user,
access to network shares, and navigation through archive file contents.

## Artifact Tree

``` text
Baggage.zip
└── Baggage
    └── C
        └── Users
            └── steve
                ├── NTUSER.DAT
                ├── ntuser.dat.LOG1
                ├── ntuser.dat.LOG2
                └── AppData
                    └── Local
                        └── Microsoft
                            └── Windows
                                ├── UsrClass.dat       ← Shellbags
                                ├── UsrClass.dat.LOG1
                                └── UsrClass.dat.LOG2
```

Main artifact:

``` text
C:\Users\steve\AppData\Local\Microsoft\Windows\UsrClass.dat
```

# Task 1

### Question

> What was the name of the archive file downloaded by the compromised
> account?

### Analysis

Open **ShellBags Explorer** and navigate to:

``` text
Desktop → This PC → Downloads
```

The Downloads folder contains a single archive file:

``` text
1.zip
```

### Answer

``` text
1.zip
```

# Task 2

### Question

> What was the name of the utility brought in by the attacker to search
> for sensitive data?

### Analysis

Navigate to:

``` text
Desktop → Shared Documents Folder (Users Files)
→ AppData → Local → Temp
→ Temp1_1.zip → 1
→ Everything-1.4.1.1028.x64.zip
```

The utility is **Everything**, a fast file and folder search utility.

### Answer

``` text
Everything 1.4.1.1028
```

# Task 3

### Question

> The attacker navigated the filesystem and found sensitive files used
> by the victim in their day-to-day work. When was the VPN folder
> accessed by the attacker?

### Hint

> Look for the Last Interacted Timestamp for the VPN directory.

### Analysis

Search for `VPN` using `Ctrl + F`.

The relevant directory is:

``` text
OT Station 3 internal VPN
```

Its Last Interacted timestamp is:

``` text
2025-09-03 07:31:05.130
```

The required answer format omits fractional seconds.

### Answer

``` text
2025-09-03 07:31:05
```

# Task 4

### Question

> What was the name of the directory containing the victim's passwords?

### Analysis

Search for `password` using `Ctrl + F`.

The relevant directory is:

``` text
OnePassword MasterPass
```

### Answer

``` text
OnePassword MasterPass
```

# Task 5

### Question

> The attacker also accessed a network share to pillage network data.
> What is the UNC path?

### Analysis

Navigate to **Computers and Devices** and inspect the relevant network
resource.

The UNC path is:

``` text
\\Prod-ns-2\prodshare
```

### Answer

``` text
\\Prod-ns-2\prodshare
```

# Task 6

### Question

> When is the dam construction planned?

### Analysis

Inside the network-share data, there is a directory named:

``` text
Construction 2027
```

The year provides the answer.

### Answer

``` text
2027
```

# Task 7

### Question

> What was the name of the archive file present on the network share?

### Analysis

Navigate to:

``` text
Desktop → Shared Documents Folder (Users Files)
→ AppData → Local → Temp
→ Temp1_a.zip → a
```

The archive found in the relevant network-share data is:

``` text
Dam Construction Engineer Plans.zip
```

### Answer

``` text
Dam Construction Engineer Plans.zip
```

# Task 8

### Question

> When was the archive file from the network share accessed?

### Analysis

Inspect the relevant network-share artifact and its **Last Interacted**
timestamp.

``` text
2025-09-03 07:34:04
```

### Answer

``` text
2025-09-03 07:34:04
```

# Task 9

### Question

> The attacker created a staging folder to prepare for collection and
> exfiltration. What is the full path of the staging folder?

### Analysis

The staging folder is located under the victim's Pictures directory and
is named:

``` text
a
```

Full path:

``` text
C:\Users\Steve\Pictures\a
```

The staging data includes:

``` text
OT Station 3 internal VPN
OnePassword MasterPass
Engineers Tab
```

### Answer

``` text
C:\Users\Steve\Pictures\a
```

# Task 10

### Question

> The attacker compressed the staging folder to prepare the data for
> exfiltration. When was the exfiltration archive file accessed?

### Analysis

The staging folder was compressed into:

``` text
a.zip
```

Its Last Interacted timestamp is:

``` text
2025-09-03 07:34:30.081
```

The required answer format omits fractional seconds.

### Answer

``` text
2025-09-03 07:34:30
```

# Final Answers

  Task   Answer
  ------ ---------------------------------------
  1      `1.zip`
  2      `Everything 1.4.1.1028`
  3      `2025-09-03 07:31:05`
  4      `OnePassword MasterPass`
  5      `\\Prod-ns-2\prodshare`
  6      `2027`
  7      `Dam Construction Engineer Plans.zip`
  8      `2025-09-03 07:34:04`
  9      `C:\Users\Steve\Pictures\a`
  10     `2025-09-03 07:34:30`

## Attack Timeline

``` text
Download archive
      ↓
    1.zip
      ↓
Obtain Everything
      ↓
Search victim filesystem
      ├── OT Station 3 internal VPN
      ├── OnePassword MasterPass
      └── Engineers Tab
      ↓
Access network share
\\Prod-ns-2\prodshare
      ↓
Find Construction 2027
      ↓
Access Dam Construction Engineer Plans.zip
      ↓
Create staging folder
C:\Users\Steve\Pictures\a
      ↓
Compress staging data
a.zip
      ↓
Prepare data for exfiltration
```

## Case Closed

The investigation demonstrates how Shellbag artifacts can reconstruct
filesystem navigation and identify evidence related to data access,
network-share activity, staging, and potential exfiltration.
