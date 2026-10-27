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

Jobs can also get docker-in-docker from a shell script mounting the docker
socket (e.g. scripts/run-in-docker.sh), directly or through a run_tests.sh
target calling it. A Groovy script or stages.yml naming such a shell script
or target is reported, too. Target names built with ${...} are matched as patterns.
"""

# ruff: noqa: T201  # It's OK for scripts to print()

import os
import re
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

SCAN_DIR = "buildscripts"
SHELL_SCRIPT_DIRS = ("buildscripts", "scripts")
RUN_TESTS = ("tests/run_tests.sh", "non-free/tests/run_tests.sh")
STAGES = "buildscripts/scripts/stages.yml"

###########################################
# Scripts that still use docker-in-docker.
# !!! DO NOT ADD TO THIS LIST !!!
###########################################
ALLOWED = frozenset(
    {
        "buildscripts/scripts/build-cmk-image.groovy",
        "buildscripts/scripts/test-integration-docker.groovy",
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
_SOCKET_MOUNT = re.compile(r"-v\s*['\"]?/var/run/docker\.sock")
_SHELL_FUNCTION = re.compile(r"^([\w-]+)\(\)\s*\{")
_INTERPOLATION = re.compile(r"(\$\{[^}]*\})")
_TOKEN = re.compile(r"[\w.${}-]+")


def _code_lines(text: str, comment: str = "//") -> list[str]:
    return [line for line in text.splitlines() if not line.lstrip().startswith(comment)]


def _name(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w.-])")


def _shell_functions(script: str) -> dict[str, str]:
    """Map the name of every function in a shell script to its body."""
    functions = {}
    name, body = None, list[str]()
    for line in _code_lines(script, "#"):
        if name is not None:
            if line.startswith("}"):
                functions[name] = "\n".join(body)
                name = None
            else:
                body.append(line)
        elif match := _SHELL_FUNCTION.match(line):
            if line.rstrip().endswith("}"):
                functions[match[1]] = line[match.end() :]
            else:
                name, body = match[1], []
    return functions


def _socket_targets(functions: dict[str, str], socket_scripts: set[str]) -> set[str]:
    """The targets calling a socket mounting script, directly or through other functions."""
    found = {
        f for f, body in functions.items() if any(_name(s).search(body) for s in socket_scripts)
    }
    while new := {
        f
        for f, body in functions.items()
        if f not in found and any(_name(g).search(body) for g in found)
    }:
        found |= new
    return {f for f in found if not f.startswith("_")}


def socket_names(root: Path) -> set[str]:
    """Names of the shell scripts and run_tests.sh targets mounting the docker socket."""
    scripts = {
        path.name
        for directory in SHELL_SCRIPT_DIRS
        for path in (root / directory).rglob("*.sh")
        if any(_SOCKET_MOUNT.search(line) for line in _code_lines(path.read_text(), "#"))
    }
    functions = {
        name: body
        for run_tests in RUN_TESTS
        if (root / run_tests).exists()
        for name, body in _shell_functions((root / run_tests).read_text()).items()
    }
    return scripts | _socket_targets(functions, scripts)


def _mentioned(lines: list[str], names: set[str]) -> set[str]:
    """The names mentioned in the lines; a ${...} matches any part of a name."""
    found = set()
    for token in (t.strip(".") for line in lines for t in _TOKEN.findall(line)):
        parts = _INTERPOLATION.split(token)
        # e.g. ${date}-${branch} names no target
        if not re.search(r"[a-z].*-|-.*[a-z]", "".join(parts[::2])):
            continue
        pattern = "".join(r"[\w-]+" if i % 2 else re.escape(part) for i, part in enumerate(parts))
        found |= {n for n in names if re.fullmatch(pattern, n)}
    return found


def _problems(path: str, groovy: str, allowed: frozenset[str], sockets: set[str]) -> list[str]:
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
    if path not in allowed:
        problems.extend(
            f"{path}: runs {name}, which mounts the docker socket"
            for name in sorted(_mentioned(lines, sockets))
        )
    return problems


def find_problems(root: Path, allowed: frozenset[str]) -> list[str]:
    sockets = socket_names(root)
    stages = root / STAGES
    stage_lines = _code_lines(stages.read_text(), "#") if stages.exists() else []
    return [
        f"{STAGES}: runs {name}, which mounts the docker socket"
        for name in sorted(_mentioned(stage_lines, sockets))
    ] + [
        problem
        for path in sorted((root / SCAN_DIR).rglob("*.groovy"))
        for problem in _problems(
            path.relative_to(root).as_posix(), path.read_text(), allowed, sockets
        )
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
