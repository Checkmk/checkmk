#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import multiprocessing
import os
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator

import pytest

from tests.testlib import cmk_path, repo_path


def test_pylint(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="cmk_pylint_") as tmpdir, capsys.disabled():
        print("\n")
        assert run_pylint(["--version"]) == 0
        print()
        assert run_pylint(construct_args(Path(tmpdir))) == 0, "Pylint found an error"


def run_pylint(args: Iterable[str]) -> int:
    cmd = ["python3", "-m", "pylint"] + list(args)
    return subprocess.run(cmd, cwd=repo_path(), check=False).returncode


def construct_args(tmpdir: Path) -> list[str]:
    args = [
        f"--rcfile={Path(repo_path()) / '.pylintrc'}",
        f"--jobs={num_jobs_to_use()}",
    ]
    if pylint_args := os.environ.get("PYLINT_ARGS"):
        args += pylint_args.split(" ")
    args.extend(str(f) for f in _get_files_to_check(tmpdir))
    return args


def num_jobs_to_use() -> int:
    # Naive heuristic, but looks OK for our use cases:\ Normal quad core CPUs
    # with HT report 8 CPUs (=> 6 jobs), our server 24-core CPU reports 48 CPUs
    # (=> 11 jobs). Just using 0 (meaning: use all reported CPUs) might just
    # work, too, but it's probably a bit too much.
    #
    # On our CI server there are currently up to 5 parallel Gerrit jobs allowed
    # which trigger pylint + 1 explicit pylint job per Checkmk branch. This
    # means that there may be up to 8 pylint running in parallel. Currently
    # these processes consume about 400 MB of rss memory.  To prevent swapping
    # we need to reduce the parallelization of pylint for the moment.
    if os.environ.get("USER") == "jenkins":
        return int(multiprocessing.cpu_count() / 8.0) + 3
    return int(multiprocessing.cpu_count() / 8.0) + 5


def _get_files_to_check(tmpdir: Path) -> Sequence[Path]:
    # Add the compiled files for things that are no modules yet
    (tmpdir / "__init__.py").touch()
    _compile_check_plugins(tmpdir)

    # Not checking compiled check, inventory, bakery plugins with Python 3
    files = [tmpdir]

    completed_process = subprocess.run(
        [f"{repo_path()}/scripts/find-python-files"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=False,
    )

    for fname in completed_process.stdout.splitlines():
        # Thin out these excludes some day...
        rel_path = fname[len(repo_path()) + 1 :]

        # Can currently not be checked alone. Are compiled together below
        if rel_path.startswith("checks/"):
            continue

        # TODO: We should also test them...
        if (
            rel_path == "werk"
            or rel_path.startswith("scripts/")
            or rel_path.startswith("agents/wnx/tests/regression/")
        ):
            continue

        # TODO: disable random, not that important stuff
        if (
            rel_path.startswith("agents/windows/it/")
            or rel_path.startswith("agents/windows/msibuild/")
            or rel_path.startswith("doc/")
            or rel_path.startswith("livestatus/api/python/example")
            or rel_path.startswith("livestatus/api/python/make_")
        ):
            continue

        files.append(Path(fname))

    return files


def _compile_check_plugins(pylint_test_dir: Path) -> None:
    for idx, f_name in enumerate(check_files(Path(repo_path()) / "checks")):
        with stand_alone_template(pylint_test_dir / f"cmk_checks_{idx}.py") as file_handle:
            add_file(file_handle, f_name)


def check_files(base_dir: Path) -> Sequence[Path]:
    return sorted(Path(base_dir) / f for f in os.listdir(base_dir) if not f.startswith("."))


@contextlib.contextmanager
def stand_alone_template(file_name: Path) -> Iterator[TextIOWrapper]:
    with file_name.open(mode="w") as file_handle:
        # Fake data structures where checks register (See cmk/base/checks.py)
        file_handle.write(
            """
# -*- encoding: utf-8 -*-

from cmk.base.check_api import *  # pylint: disable=wildcard-import,unused-wildcard-import


check_info                         = {}
check_includes                     = {}
precompile_params                  = {}
check_default_levels               = {}
factory_settings                   = {}
check_config_variables             = []
snmp_info                          = {}
snmp_scan_functions                = {}
active_check_info                  = {}
special_agent_info                 = {}

"""
        )
        # These pylint warnings are incompatible with our "concatenation technology".
        disable_pylint = [
            "function-redefined",
            "pointless-string-statement",
            "redefined-outer-name",
            "reimported",
            "ungrouped-imports",
            "unused-variable",
            "wrong-import-order",
            "wrong-import-position",
        ]
        file_handle.write(f"# pylint: disable={','.join(disable_pylint)}\n")
        yield file_handle


def add_file(f: TextIOWrapper, path: Path) -> None:
    relpath = os.path.relpath(os.path.realpath(path), cmk_path())
    f.write("# -*- encoding: utf-8 -*-")
    f.write("#\n")
    f.write("# ORIG-FILE: " + relpath + "\n")
    f.write("#\n")
    f.write("\n")
    f.write(path.read_text())
