#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Recompute SHA256 hashes for the five python.org per-feature MSIs.

Run after bumping ``PYTHON_VERSION_WINDOWS`` in ``defines.make``.
Prints the ``http_file(...)`` blocks ready to paste into ``MODULE.bazel``.

Usage:
    python3 agents/modules/windows/refresh_msi_pins.py 3.13.13
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request

# MSIs the Bazel rule depends on.  Mirrors _DEFAULT_MSIS in python_cab.bzl;
# keep the two in lockstep.
MSIS = ("ucrt", "core", "exe", "lib", "pip")


def fetch_sha256(url: str) -> str:
    sha = hashlib.sha256()
    with urllib.request.urlopen(url) as fh:  # nosec B310 # BNS:28af27
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "python_version",
        help="Full Windows Python version, e.g. 3.13.13",
    )
    args = parser.parse_args()

    print(f"# Refreshed for CPython {args.python_version} via {sys.argv[0]}")
    for name in MSIS:
        url = f"https://www.python.org/ftp/python/{args.python_version}/amd64/{name}.msi"
        sha = fetch_sha256(url)
        print(
            f"http_file(\n"
            f'    name = "python_msi_{name}",\n'
            f'    sha256 = "{sha}",\n'
            f'    url = "{url}",\n'
            f")"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
