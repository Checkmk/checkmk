#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This script checks the deps before and after running `make relock_venv` and writes the diff to a
file to be then picked up as git commit message."""

import argparse
import io
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO

type Hash = str


@dataclass(frozen=True, order=True, kw_only=True)
class Info:
    name: str
    version: str
    hashes: list[Hash]


def _parse_requirements(path: Path) -> Mapping[str, Info]:
    with path.open() as rfile:
        return _parse_requirements_file(rfile)


def _parse_requirements_file(requirements_file: IO[str]) -> Mapping[str, Info]:
    infos: dict[str, Info] = {}
    while raw_line := requirements_file.readline():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--"):
            assert line.startswith("--index-url")
            continue

        # Remove extras before splitting, they can contain spaces, e.g. pyjwt[crypto] or
        # pydantic-ai-slim[anthropic, openai]
        requirement = re.sub(r"\[[^\]]*\]", "", line, count=1)
        name, version = requirement.replace(" @ git+", "==git+").split(maxsplit=1)[0].split("==", 1)
        info = Info(name=name, version=version, hashes=[])

        while line.endswith("\\"):
            line = requirements_file.readline().strip()
            assert line.startswith("--hash=sha256:")
            info.hashes.append(line.removeprefix("--hash=sha256:").removesuffix("\\").strip())
        infos[info.name] = info
    return infos


def _diff(before: Mapping[str, Info], after: Mapping[str, Info]) -> str:
    deleted = before.keys() - after.keys()
    added = after.keys() - before.keys()
    updated = {(v.name, v.version) for v in after.values() if v.name not in added} - {
        (v.name, v.version) for v in before.values()
    }
    return_value = ""
    if deleted:
        return_value = "\n".join(f"{d} removed" for d in sorted(deleted)) + "\n\n"

    # no updates seems unreasonable
    for lib, to_version in sorted(updated):
        before_version = before[lib].version
        return_value += f"{lib} updated from {before_version} to {to_version}\n"
    return_value += "\n"

    if added:
        return_value += "\n".join(
            f"{added_dep.name} {added_dep.version} added"
            for added_dep in sorted(a for a in after.values() if a.name in added)
        )
    return return_value


def test_parse_requirements_file() -> None:
    assert _parse_requirements_file(
        io.StringIO(
            "pydantic-ai-slim[anthropic, openai]==2.56.0 \\\n"
            "    --hash=sha256:abc \\\n"
            "    --hash=sha256:def\n"
            "pyjwt[crypto]==2.15.1 \\\n"
            "    --hash=sha256:123\n"
            'foo==1.0 ; python_version < "3.13"\n'
            "six==1.17.0\n"
        )
    ) == {
        "pydantic-ai-slim": Info(name="pydantic-ai-slim", version="2.56.0", hashes=["abc", "def"]),
        "pyjwt": Info(name="pyjwt", version="2.15.1", hashes=["123"]),
        "foo": Info(name="foo", version="1.0", hashes=[]),
        "six": Info(name="six", version="1.17.0", hashes=[]),
    }


def test_diff() -> None:
    assert (
        _diff(
            {
                "a": Info(name="a", version="1.0", hashes=[]),
                "b": Info(name="b", version="1.0", hashes=[]),
                "c": Info(name="c", version="1.0", hashes=[]),
            },
            {
                "a": Info(name="a", version="1.0", hashes=[]),
                "c": Info(name="c", version="2.0", hashes=[]),
                "d": Info(name="d", version="1.0", hashes=[]),
            },
        )
        == "b removed\n\n"
        "c updated from 1.0 to 2.0\n\n"
        "d 1.0 added"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update Python libraries and make a nice commit message"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Call git commit with the generated message",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--with-windows",
        action="store_true",
        help="Also update the Windows agent module lock file",
    )
    scope.add_argument(
        "--windows-only",
        action="store_true",
        help="Only update the Windows agent module lock file",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--yolo",
        action="store_true",
        help="Update everything, allowing major updates (default: compatible releases only)",
    )
    mode.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Only update the given package(s), as far as possible; everything else stays "
        "within compatible releases",
    )
    return parser.parse_args()


# The license list has to cover all editions. Using the same configuration for every bazel call
# keeps the analysis cache instead of discarding it on each edition switch.
_BAZEL_FLAGS = ["--cmk_edition=ultimate"]
_LICENSES_FILE = "omd/dependency_management/automatically_researched_licenses.json"


def _bazel_run(target: str, *args: str) -> None:
    subprocess.check_call(["bazel", "run", *_BAZEL_FLAGS, target, "--", *args])


def _get_lock_files() -> list[str]:
    return [
        filename
        for filename in subprocess.check_output(
            [
                "bazel",
                "cquery",
                *_BAZEL_FLAGS,
                'kind("source file", deps(//:lock_python_requirements))',
                "--output=files",
            ],
            text=True,
        ).splitlines()
        if "requirements" in filename and filename.endswith(".txt")
    ]


@dataclass(frozen=True)
class LockGroup:
    lock_file: Path
    target: str
    # locks constrained by lock_file, they just need to be regenerated afterwards
    derived_targets: tuple[str, ...] = ()
    commit_msg_heading: str = ""


def _lock_groups(with_windows: bool, windows_only: bool) -> list[LockGroup]:
    root = LockGroup(
        lock_file=Path("requirements.txt"),
        target="//:requirements",
        derived_targets=("//:community_requirements", "//:runtime_requirements")
        + (
            ("//omd/non-free/relay:requirements",)
            if Path("omd/non-free/relay/BUILD").exists()
            else ()
        ),
    )
    windows = LockGroup(
        lock_file=Path("agents/modules/windows/requirements-windows.txt"),
        target="//agents/modules/windows:requirements_windows",
        commit_msg_heading="requirements-windows.txt:\n",
    )
    if windows_only:
        return [windows]
    return [root, windows] if with_windows else [root]


@contextmanager
def _constraints_file(lock: Mapping[str, Info]) -> Iterator[Path]:
    """Pin every package of the lock to its compatible release"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as f:
        f.writelines(
            f"{info.name}{'~=' if '.' in info.version else '=='}{info.version}\n"
            for info in lock.values()
        )
        f.flush()
        yield Path(f.name)


def _relock(group: LockGroup, packages: list[str], yolo: bool) -> str:
    """Update the lock files of the group and return the diff of the leading lock file"""
    before = _parse_requirements(group.lock_file)
    if packages:
        _bazel_run(group.target, *(arg for p in packages for arg in ("--upgrade-package", p)))
    elif yolo:
        group.lock_file.write_text("")
        _bazel_run(group.target)
    else:
        group.lock_file.write_text("")
        with _constraints_file(before) as constraints:
            _bazel_run(group.target, "--constraint", str(constraints))
    # The plain rerun keeps the resolved versions but drops the temporary constraints file from
    # the "via" annotations, so the lock matches what the lock test regenerates.
    for target in (group.target, *group.derived_targets):
        _bazel_run(target)
    return _diff(before, _parse_requirements(group.lock_file))


def _main() -> None:
    args = _parse_args()
    groups = _lock_groups(args.with_windows, args.windows_only)
    diffs = [_relock(group, args.packages or [], args.yolo) for group in groups]
    # there is also a omd/requirements_lock.txt file, it looks like it will vanish soon
    # I'm not sure how we would want to update that anyways. Special commit or all in one?
    # Therefore let's keep it simple for now.
    # Relocking would work like this:
    # echo > omd/requirements_lock.txt; bazel run //omd:requirements_lock
    with open(".git-commit-msg", "w") as f:
        f.write("Update Python libraries\n\n")
        f.write(
            "\n\n".join(
                f"{group.commit_msg_heading}{diff}"
                for group, diff in zip(groups, diffs)
                if diff.strip() or group is groups[0]
            )
        )
    # A failed lookup must not throw away the relock, the licenses can be researched by hand.
    try:
        _bazel_run("//omd/dependency_management:research_licenses")
    except subprocess.CalledProcessError:
        print(f"License research failed, {_LICENSES_FILE} needs manual care", file=sys.stderr)
    if args.commit:
        subprocess.check_call(["git", "add", _LICENSES_FILE, *_get_lock_files()])
        subprocess.check_call(["git", "commit", "-F", ".git-commit-msg"])
    else:
        print("git commit -F .git-commit-msg")


if __name__ == "__main__":
    _main()
