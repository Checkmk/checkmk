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


def _find_pipfile_locks() -> Sequence[Path]:
    """return a list of paths where we found Pipfile.locks"""
    return sorted(
        (
            Path(p)
            for p in subprocess.check_output(
                ["find", ".", "-name", "Pipfile.lock", "-type", "f"], text=True
            ).splitlines()
        ),
        key=lambda p: len(p.parents),
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


def _commit_piplock(piplock_path: Path, version_diff: Sequence[UpdateInfo]) -> None:
    subprocess.run(
        ["git", "add", "Pipfile.lock"],
        cwd=piplock_path.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    message = f"pipenv lock{"" if (p := piplock_path.parent) == Path() else f" in {p}"}\n\n"
    message += "\n".join(
        f"{info.name}: {info.from_version} -> {info.to_version}" for info in version_diff
    )
    message += "\n"

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=piplock_path.parent,
        check=True,
    )


def _handle_piplock(task_queue: queue.Queue[Path], lock: threading.Lock) -> None:
    while True:
        piplock_path = task_queue.get()
        if version_diff := _update_piplock(piplock_path):
            with lock:  # only one thread should commit at a time
                _commit_piplock(piplock_path, version_diff)

        task_queue.task_done()


if __name__ == "__main__":
    N_THREADS = 12
    logging.basicConfig(level=logging.INFO)

    commit_lock = threading.Lock()
    tasks = queue.Queue[Path]()

    for _ in range(N_THREADS):
        threading.Thread(target=_handle_piplock, args=(tasks, commit_lock), daemon=True).start()

    for path in _find_pipfile_locks():
        tasks.put(path)

    tasks.join()
