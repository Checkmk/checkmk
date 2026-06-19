#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Patches the ELF files inside a wheel and writes a new wheel.

Each entry's metadata (Unix mode, timestamp, compression) is preserved, and the
RECORD file's hashes/sizes are recomputed so the result is a valid wheel.
"""

import base64
import hashlib
import os
import posixpath
import subprocess
import sys
import tempfile
import zipfile

from runpath_patch import depth_relative_rpath, is_elf


def _patch_blob(blob: bytes, patchelf: str, rpath: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(blob)
        path = tmp.name
    try:
        subprocess.run([patchelf, "--set-rpath", rpath, path], check=True)
        with open(path, "rb") as patched:
            return patched.read()
    finally:
        os.unlink(path)


def _update_record(contents: dict[str, bytes]) -> None:
    record_names = [name for name in contents if name.endswith(".dist-info/RECORD")]
    if not record_names:
        return
    record_name = record_names[0]
    lines = []
    for line in contents[record_name].decode("utf-8").splitlines():
        if not line:
            continue
        path = line.split(",", 1)[0]
        if path == record_name or path not in contents:
            # Leave RECORD's own (hashless) entry and any unlisted file as-is.
            lines.append(line)
            continue
        blob = contents[path]
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(blob).digest()).rstrip(b"=").decode("ascii")
        )
        lines.append(f"{path},sha256={digest},{len(blob)}")
    contents[record_name] = ("\n".join(lines) + "\n").encode("utf-8")


def main() -> None:
    src_whl, out_whl, patchelf, base_rpath = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    with zipfile.ZipFile(src_whl) as zin:
        infos = zin.infolist()
        contents: dict[str, bytes] = {}
        for info in infos:
            if info.is_dir():
                continue
            blob = zin.read(info.filename)
            if is_elf(blob):
                rel_dir = (posixpath.dirname(info.filename) or ".").replace("/", os.sep)
                blob = _patch_blob(blob, patchelf, depth_relative_rpath(base_rpath, rel_dir))
            contents[info.filename] = blob

    _update_record(contents)

    # Reuse each source ZipInfo so the Unix mode (external_attr), timestamp and
    # per-entry compression are carried over verbatim into the new wheel.
    with zipfile.ZipFile(out_whl, "w") as zout:
        for info in infos:
            zout.writestr(info, b"" if info.is_dir() else contents[info.filename])


if __name__ == "__main__":
    main()
