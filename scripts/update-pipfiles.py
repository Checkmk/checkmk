#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""update Pipfile.lock|s in the cmk repo"""

import json
import logging
import os
import queue
import subprocess
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import NamedTuple

environment = os.environ.copy()
environment.update({"PIPENV_PYPI_MIRROR": "https://pypi.org/simple"})


class UpdateInfo(NamedTuple):
    """information about a package update"""

    name: str
    from_version: str
    to_version: str


@dataclass
class LockPaths:
    pipfile_lock: Path
    requirement_lock: Path | None = None

    def __init__(self, p: Path):
        self.pipfile_lock = p
        requirements_lock = Path(p.parents[0] / "requirements_lock.txt")
        if requirements_lock.exists():
            self.requirement_lock = requirements_lock


class CommitInfo(NamedTuple):
    file_to_be_committed: Path
    update_info: Sequence[UpdateInfo]


def _find_locks() -> Sequence[LockPaths]:
    """return a list of paths where we found Pipfile.locks and - if residing next to it - a requirements_lock.txt"""
    return sorted(
        (
            LockPaths(Path(p))
            for p in subprocess.check_output(
                ["find", ".", "-name", "Pipfile.lock", "-type", "f"], text=True
            ).splitlines()
        ),
        key=lambda p: len(p.pipfile_lock.parents),
        reverse=True,
    )


def _parse_pipenv_lock(piplock_path: Path) -> dict[str, str]:
    """return a dictionary of package names to versions"""
    with piplock_path.open() as piplock_file:
        info = json.load(piplock_file)

    return {
        package: package_info["version"].lstrip("=")
        for package, package_info in chain(
            info.get("default", {}).items(), info.get("develop", {}).items()
        )
        if "path" not in package_info
    }


def _parse_requirements_lock(requirements_lock: Path) -> dict[str, str]:
    """return a dictionary of package names to versions"""
    with requirements_lock.open() as requirements_lock_file:
        return {
            line.split("==")[0]: line.split("==")[1].split()[0].strip()
            for line in requirements_lock_file
            if not line.startswith("#") and "==" in line
        }


def _diff_versions(before: dict[str, str], after: dict[str, str]) -> Sequence[UpdateInfo]:
    """diff to parsed pipenv lock files"""
    return [
        UpdateInfo(name=name, from_version=before[name], to_version=after[name])
        for name in before
        if name in after and before[name] != after[name]
    ]


def _update_piplock(piplock_path: Path) -> Sequence[UpdateInfo]:
    logging.info("Updating %s", piplock_path)
    before_versions = _parse_pipenv_lock(piplock_path)
    subprocess.run(
        ["pipenv", "lock", "--dev"],
        cwd=piplock_path.parent,
        check=True,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    after_versions = _parse_pipenv_lock(piplock_path)
    changed_versions = _diff_versions(before_versions, after_versions)
    for info in changed_versions:
        logging.info("%s: %s -> %s", info.name, info.from_version, info.to_version)
    return changed_versions


def _update_requirementslock(requirements_lock: Path) -> Sequence[UpdateInfo]:
    logging.info("Updating %s", requirements_lock)
    before_versions = _parse_requirements_lock(requirements_lock)
    subprocess.run(
        ["bazel", "run", ":requirements.update"],
        cwd=requirements_lock.parent,
        check=True,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    after_versions = _parse_requirements_lock(requirements_lock)
    changed_versions = _diff_versions(before_versions, after_versions)
    for info in changed_versions:
        logging.info("%s: %s -> %s", info.name, info.from_version, info.to_version)
    return changed_versions


def _commit_lock(commit_infos: Sequence[CommitInfo]) -> None:
    message = f"lock python dependencies{"" if (p := commit_infos[0].file_to_be_committed.parent) == Path() else f" in {p}"}\n\n"
    for ci in commit_infos:
        subprocess.run(
            ["git", "add", ci.file_to_be_committed.name],
            cwd=ci.file_to_be_committed.parent,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        message += f"\n{ci.file_to_be_committed.name} update:\n"
        message += "\n".join(
            f"* {info.name}: {info.from_version} -> {info.to_version}" for info in ci.update_info
        )
    message += "\n"

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=commit_infos[0].file_to_be_committed.parent,
        check=True,
    )


def _handle_lock_files(task_queue: queue.Queue[LockPaths], lock: threading.Lock) -> None:
    while True:
        lock_files = task_queue.get()
        commit_infos = []
        if lock_files.requirement_lock is not None and (
            version_diff_req := _update_requirementslock(lock_files.requirement_lock)
        ):
            commit_infos.append(CommitInfo(lock_files.requirement_lock, version_diff_req))
        if version_diff_pipfile := _update_piplock(lock_files.pipfile_lock):
            commit_infos.append(CommitInfo(lock_files.pipfile_lock, version_diff_pipfile))
        if commit_infos:
            with lock:  # only one thread should commit at a time
                _commit_lock(commit_infos)

        task_queue.task_done()


if __name__ == "__main__":
    N_THREADS = 12
    logging.basicConfig(level=logging.INFO)

    commit_lock = threading.Lock()
    tasks = queue.Queue[LockPaths]()

    for _ in range(N_THREADS):
        threading.Thread(target=_handle_lock_files, args=(tasks, commit_lock), daemon=True).start()

    for lock_paths in _find_locks():
        tasks.put(lock_paths)

    tasks.join()
