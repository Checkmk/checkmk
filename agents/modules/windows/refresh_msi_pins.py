#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Recompute SHA256 hashes for the five python.org per-feature MSIs.

Run after bumping ``PYTHON_VERSION_WINDOWS`` in ``package_versions.bzl``.
Prints the ``_MSI_SHA256`` map ready to paste over the one in
``//bazel/extensions:python_cab_repositories.bzl``, which derives the URLs from
``PYTHON_VERSION_WINDOWS`` itself.

The version needs no argument: the ``py_binary`` passes ``PYTHON_VERSION_WINDOWS``
via ``args``, so the hashes are always fetched for the version the extension will
actually request.

Usage:
    bazel run //agents/modules/windows:refresh_msi_pins

To see the hashes for a version before committing to it, override:

    bazel run //agents/modules/windows:refresh_msi_pins -- --python-version=3.14.0
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
        "--python-version",
        required=True,
        help="Full Windows Python version, e.g. 3.13.14.  Supplied by the py_binary's "
        "args from PYTHON_VERSION_WINDOWS; pass it again to override.",
    )
    args = parser.parse_args()

    print(f"# sha256 of each per-feature MSI, for PYTHON_VERSION_WINDOWS {args.python_version}.")
    print("_MSI_SHA256 = {")
    # Sorted, so the pasted map is already buildifier-clean.
    for name in sorted(MSIS):
        url = f"https://www.python.org/ftp/python/{args.python_version}/amd64/{name}.msi"
        print(f'    "{name}": "{fetch_sha256(url)}",')
    print("}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
