#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Check the modules of our local Bazel registry (bazel/thirdparty).

Every overlay file and patch of a module is pinned by an SRI hash in its
source.json. Bazel only reads such a file when its hash is not in the
repository cache, so a stale hash goes unnoticed on machines (and CI nodes)
that fetched the module before, and breaks the build everywhere else. A file
that is not listed in source.json at all is silently never used.

This compares the hashes of all modules with the files, offline. Fetching the
changed modules without repository cache (source archive, patches apply) is
done by the "Bazel local registry modules" stage in stages.yml.
"""

import base64
import hashlib
import json
import os
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

REGISTRY = Path("bazel/thirdparty")
PINNED_GROUPS = ("overlay", "patches")


def _sri(path: Path) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(path.read_bytes()).digest()).decode()


def find_problems(registry: Path) -> list[str]:
    problems = []
    for source_json in sorted(registry.glob("modules/*/*/source.json")):
        module_dir = source_json.parent
        source = json.loads(source_json.read_text())
        for group in PINNED_GROUPS:
            group_dir = module_dir / group
            pinned = source.get(group, {})
            for name, wanted in pinned.items():
                path = group_dir / name
                if not path.is_file():
                    problems.append(f"{path}: listed in {source_json}, but missing")
                elif (actual := _sri(path)) != wanted:
                    problems.append(f"{path}: hash is {actual}, {source_json} wants {wanted}")
            for path in sorted(group_dir.rglob("*")) if group_dir.is_dir() else []:
                if path.is_file() and str(path.relative_to(group_dir)) not in pinned:
                    problems.append(f"{path}: not listed in {source_json}")
    return problems


def main(argv: Sequence[str]) -> int:
    parser = ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)

    if workspace := os.environ.get("BUILD_WORKSPACE_DIRECTORY"):
        os.chdir(workspace)

    problems = find_problems(args.registry)
    for problem in problems:
        print(problem)
    if problems:
        print("Update source.json (after formatting the overlay files).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
