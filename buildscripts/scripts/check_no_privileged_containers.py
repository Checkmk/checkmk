#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Check that no Jenkins Groovy script uses a privileged container.

`privileged: true` makes inside_container() mount the host's docker socket,
i.e. the job uses docker-in-docker. Every Groovy file below buildscripts/ is
checked, job scripts as well as the helpers they load. No script may mount
the docker socket itself, and inside_container() must not be privileged by
default.
"""

# ruff: noqa: T201  # It's OK for scripts to print()

import os
import re
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

SCAN_DIR = "buildscripts"

###########################################
# Scripts that still use docker-in-docker.
# !!! DO NOT ADD TO THIS LIST !!!
###########################################
ALLOWED = frozenset(
    {
        "buildscripts/scripts/build-cmk-image.groovy",
        "buildscripts/scripts/test-system-agent-updates.groovy",
        "buildscripts/scripts/test-system-gui-single-node.groovy",
        "buildscripts/scripts/test-system-mk-oracle.groovy",
        "buildscripts/scripts/test-system-relay.groovy",
        "buildscripts/scripts/test-system-singlesite-single-node.groovy",
        "buildscripts/scripts/utils/upload_artifacts.groovy",
    }
)

# inside_container() mounts the docker socket here if privileged is set
HELPER = "buildscripts/scripts/utils/docker_image_aliases_helper.groovy"

_PRIVILEGED = re.compile(r"\bprivileged\s*:\s*true\b")
_DOCKER_SOCKET = re.compile(r"\bdocker\.sock\b")
_UNPRIVILEGED_DEFAULT = re.compile(r'args\.get\("privileged",\s*false\)')


def _code_lines(groovy: str) -> list[str]:
    return [line for line in groovy.splitlines() if not line.lstrip().startswith("//")]


def _problems(path: str, groovy: str, allowed: frozenset[str]) -> list[str]:
    lines = _code_lines(groovy)
    if path == HELPER:
        if any(_UNPRIVILEGED_DEFAULT.search(line) for line in lines):
            return []
        return [f'{path}: privileged must default to false (args.get("privileged", false))']
    problems = []
    if path not in allowed and any(_PRIVILEGED.search(line) for line in lines):
        problems.append(f"{path}: uses a privileged container (privileged: true)")
    if any(_DOCKER_SOCKET.search(line) for line in lines):
        problems.append(f"{path}: mounts the docker socket")
    return problems


def find_problems(root: Path, allowed: frozenset[str]) -> list[str]:
    return [
        problem
        for path in sorted((root / SCAN_DIR).rglob("*.groovy"))
        for problem in _problems(path.relative_to(root).as_posix(), path.read_text(), allowed)
    ]


def main(argv: Sequence[str]) -> int:
    ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)

    root = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    problems = find_problems(root, ALLOWED)
    for problem in problems:
        print(problem)
    if problems:
        print("CI jobs must not use docker-in-docker.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
