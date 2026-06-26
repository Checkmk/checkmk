#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Update the pinned NagVis release to the latest GitHub release.

Queries the GitHub releases API for the latest NagVis release, downloads the
release tarball, computes its SHA256 and rewrites the ``nagvis`` ``http_archive``
block in ``MODULE.bazel`` (sha256, strip_prefix and download URLs). The
``version`` field of the ``dependency_info`` rule in ``BUILD.nagvis.bazel`` is
updated as well.

After running, review the diff, build the package and create a werk, e.g.::

    bazel build @nagvis//:pkg_tar

Usage:
    python3 omd/packages/nagvis/update_nagvis.py            # update to latest
    python3 omd/packages/nagvis/update_nagvis.py 1.10.4     # update to a version
    python3 omd/packages/nagvis/update_nagvis.py --check    # report only
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

GITHUB_API_LATEST = "https://api.github.com/repos/NagVis/nagvis/releases/latest"
DOWNLOAD_URL = "https://github.com/NagVis/nagvis/releases/download/nagvis-{v}/nagvis-{v}.tar.gz"

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_BAZEL = REPO_ROOT / "MODULE.bazel"
BUILD_BAZEL = Path(__file__).resolve().parent / "BUILD.nagvis.bazel"


def fetch_latest_version() -> str:
    """Return the latest NagVis version, e.g. ``1.10.4``."""
    req = urllib.request.Request(
        GITHUB_API_LATEST, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req) as fh:  # nosec B310 # BNS:28af27
        data = json.load(fh)
    tag = str(data["tag_name"])  # e.g. "nagvis-1.10.4"
    return tag.removeprefix("nagvis-")


def fetch_sha256(url: str) -> str:
    sha = hashlib.sha256()
    with urllib.request.urlopen(url) as fh:  # nosec B310 # BNS:28af27
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def current_version() -> str:
    match = re.search(r'strip_prefix = "nagvis-([0-9.]+)"', MODULE_BAZEL.read_text())
    if not match:
        sys.exit("Could not determine current NagVis version from MODULE.bazel")
    return match.group(1)


def update_module_bazel(version: str, sha256: str) -> None:
    text = MODULE_BAZEL.read_text()

    # Limit replacements to the nagvis http_archive block to avoid touching
    # other archives that may share version numbers.
    block = re.search(r'http_archive\(\n    name = "nagvis",.*?\n\)\n', text, re.DOTALL)
    if not block:
        sys.exit("Could not locate the nagvis http_archive block in MODULE.bazel")
    original = block.group(0)

    updated = re.sub(r'sha256 = "[0-9a-f]+"', f'sha256 = "{sha256}"', original)
    updated = re.sub(
        r'strip_prefix = "nagvis-[0-9.]+"', f'strip_prefix = "nagvis-{version}"', updated
    )
    updated = re.sub(r"nagvis-[0-9.]+\.tar\.gz", f"nagvis-{version}.tar.gz", updated)
    updated = re.sub(r"download/nagvis-[0-9.]+/", f"download/nagvis-{version}/", updated)

    MODULE_BAZEL.write_text(text.replace(original, updated))


def update_build_bazel(version: str) -> None:
    text = BUILD_BAZEL.read_text()
    text = re.sub(r'version = "[0-9.]+",', f'version = "{version}",', text, count=1)
    BUILD_BAZEL.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        nargs="?",
        help="version to pin (e.g. 1.10.4); defaults to the latest GitHub release",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="only report the current and latest version, do not modify files",
    )
    args = parser.parse_args()

    current = current_version()
    target = args.version or fetch_latest_version()

    print(f"Current pinned version: {current}")
    print(f"Target version:         {target}")

    if args.check:
        if current == target:
            print("NagVis is up to date.")
        else:
            print("An update is available.")
        return

    if current == target:
        print("Nothing to do: already at the target version.")
        return

    url = DOWNLOAD_URL.format(v=target)
    print(f"Downloading {url} ...")
    sha256 = fetch_sha256(url)
    print(f"sha256: {sha256}")

    update_module_bazel(target, sha256)
    update_build_bazel(target)

    print(f"Updated MODULE.bazel and BUILD.nagvis.bazel to NagVis {target}.")
    print("Next steps: review the diff, build the package and create a werk.")


if __name__ == "__main__":
    main()
