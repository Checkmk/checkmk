#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The crlf_files() action (bazel/rules/crlf_files.bzl): copies each
source to its output with CRLF line ends.

Usage: crlf_files.py <source> <output> [<source> <output> ...]
"""

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    for source, output in zip(argv[::2], argv[1::2], strict=True):
        text = Path(source).read_bytes()
        Path(output).write_bytes(
            b"\r\n".join(line.removesuffix(b"\r") for line in text.split(b"\n"))
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
