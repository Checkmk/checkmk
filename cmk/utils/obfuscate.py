#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import argparse
from hashlib import md5
from pathlib import Path
from shutil import copyfile
from typing import Final, Tuple

from Cryptodome.Cipher import AES

#
# Format of the obfuscated file
#
# <--...body...--><mark><body-length>
# body: bytes, encrypted exe
# mark: b'CMKE', nothing
# body-length: 10-symbol string with 0-leading integer, count of bytes  to decrypt
#
OBFUSCATE_WORD: Final = b"HideAll"
OBFUSCATE_MARK: Final = b"CMKE"
OBFUSCATE_LENGTH_SIZE: Final = 10
OBFUSCATE_MARK_SIZE: Final = 4
OBFUSCATE_MARK_OFFSET: Final = -(OBFUSCATE_MARK_SIZE + OBFUSCATE_LENGTH_SIZE)
OBFUSCATE_LENGTH_OFFSET: Final = -OBFUSCATE_LENGTH_SIZE


def derive_key_and_iv(password: bytes, key_length: int, iv_length: int) -> Tuple[bytes, bytes]:
    d = d_i = b""
    while len(d) < key_length + iv_length:
        md5_block = md5(d_i + password)
        d_i = md5_block.digest()
        d += d_i
    return d[:key_length], d[key_length : key_length + iv_length]


def deobfuscate_data(data: bytes) -> bytes:
    key, iv = derive_key_and_iv(OBFUSCATE_WORD, 32, AES.block_size)

    decryption_suite = AES.new(key, AES.MODE_CBC, iv)
    return decryption_suite.decrypt(data)


def obfuscate_data(data: bytes) -> bytes:
    key, iv = derive_key_and_iv(OBFUSCATE_WORD, 32, AES.block_size)
    encryption_suite = AES.new(key, AES.MODE_CBC, iv)
    pad = len(data)
    pad = (pad // AES.block_size + 1) * AES.block_size
    to_obfuscate = data.ljust(pad)
    return encryption_suite.encrypt(to_obfuscate)


def is_data_obfuscated(data: bytes) -> bool:
    return (
        len(data) > (OBFUSCATE_MARK_SIZE + OBFUSCATE_LENGTH_SIZE)
        and data[OBFUSCATE_MARK_OFFSET:OBFUSCATE_LENGTH_OFFSET] == OBFUSCATE_MARK
    )


def obfuscate_file(file_in: Path, *, file_out: Path) -> int:
    if not file_in.exists():
        return 5

    data = file_in.read_bytes()
    if is_data_obfuscated(data):
        if file_in != file_out:
            copyfile(file_in, file_out)
        return 0

    obfuscated_data = obfuscate_data(data)
    if len(obfuscated_data) > 0:
        with file_out.open("wb") as f:
            f.write(obfuscated_data)
            f.write(f"{OBFUSCATE_MARK.decode()}{len(data):010d}".encode())
        return 0

    return 3


def deobfuscate_file(file_in: Path, *, file_out: Path) -> int:
    file_in = Path(file_in)
    if not file_in.exists():
        return 2

    data_in = file_in.read_bytes()
    if not is_data_obfuscated(data_in):
        if file_in != file_out:
            copyfile(file_in, file_out)
        return 0

    length = int(data_in[OBFUSCATE_LENGTH_OFFSET:])

    data = deobfuscate_data(data_in[:OBFUSCATE_MARK_OFFSET])
    if len(data) > 0:
        with file_out.open("wb") as f:
            f.write(data[:length])
        return 0

    return 3


# MAIN:
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="obfuscates or deobfuscates the file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-obfuscate", action="store_true")
    group.add_argument("-deobfuscate", action="store_true")
    parser.add_argument("file_in", type=Path, help="input file")
    parser.add_argument("file_out", type=Path, help="output file")
    args = parser.parse_args()
    if args.obfuscate:
        exit(obfuscate_file(args.file_in, file_out=args.file_out))
    if args.deobfuscate:
        exit(deobfuscate_file(args.file_in, file_out=args.file_out))
    else:
        exit(1)
