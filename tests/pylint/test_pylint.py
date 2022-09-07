#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import multiprocessing
import os
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

import pytest

from tests.testlib import repo_path


def test_pylint(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="cmk_pylint_") as tmpdir, capsys.disabled():
        print("\n")
        assert run_pylint(["--version"]) == 0
        print()
        assert run_pylint(construct_args(Path(tmpdir))) == 0, "Pylint found an error"


def run_pylint(args: Iterable[str]) -> int:
    cmd = ["python3", "-m", "pylint"] + list(args)
    return subprocess.run(cmd, cwd=Path(repo_path()), check=False).returncode


def construct_args(tmpdir: Path) -> list[str]:
    args = [
        f"--rcfile={Path(repo_path()) / '.pylintrc'}",
        f"--jobs={num_jobs_to_use()}",
    ]
    if pylint_args := os.environ.get("PYLINT_ARGS"):
        args += pylint_args.split(" ")
    args.extend(str(f) for f in get_files_to_check(tmpdir))
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


def get_files_to_check(tmpdir: Path) -> Iterable[Path]:
    return [compile_check_plugins(tmpdir)] + [f for f in find_python_files() if not blacklisted(f)]


def find_python_files() -> Iterable[Path]:
    return (
        make_relative(Path(f))
        for f in subprocess.run(
            [f"{Path(repo_path())}/scripts/find-python-files"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        ).stdout.splitlines()
    )


def make_relative(name: Path) -> Path:
    return name.relative_to(Path(repo_path()))


def blacklisted(name: Path) -> bool:
    return (
        # Can currently not be checked alone. Are compiled together below
        name.is_relative_to("checks")
        # TODO: We should also test them...
        or name == Path("werk")
        or name.is_relative_to("scripts")
        or name.is_relative_to("agents/wnx/tests/regression")
        # TODO: disable random, not that important stuff
        or name.is_relative_to("agents/windows/it")
        or name.is_relative_to("agents/windows/msibuild")
        or name.is_relative_to("doc")
        or name == Path("livestatus/api/python/example.py")
        or name == Path("livestatus/api/python/example_multisite.py")
        or name == Path("livestatus/api/python/make_nagvis_map.py")
    )


def compile_check_plugins(tmpdir: Path) -> Path:
    tmpdir /= LEGACY_PACKAGE_NAME
    tmpdir.mkdir()
    (tmpdir / "__init__.py").touch()
    for idx, name in enumerate(check_files()):
        with (tmpdir / f"cmk_checks_{idx}.py").open(mode="w") as f:
            f.write(HEADER)
            f.write(f"# ORIG-FILE: {make_relative(name)}\n")
            f.write(name.read_text())
    return tmpdir


def check_files() -> Iterable[Path]:
    return sorted(f for f in (Path(repo_path()) / "checks").glob("[!.]*"))


LEGACY_PACKAGE_NAME = "cmk_legacy_checks"

# These pylint warnings are incompatible with our "concatenation technology".
PYLINT_SUPPRESSIONS = [
    "function-redefined",
    "pointless-string-statement",
    "redefined-outer-name",
    "reimported",
    "ungrouped-imports",
    "unused-variable",
    "wrong-import-order",
    "wrong-import-position",
]

# Fake data structures where checks register (See cmk/base/checks.py)
HEADER = f"""
from cmk.base.check_api import *  # pylint: disable=wildcard-import,unused-wildcard-import


check_info                         = {{}}
check_includes                     = {{}}
precompile_params                  = {{}}
check_default_levels               = {{}}
factory_settings                   = {{}}
check_config_variables             = []
snmp_info                          = {{}}
snmp_scan_functions                = {{}}
active_check_info                  = {{}}
special_agent_info                 = {{}}

# pylint: disable={','.join(PYLINT_SUPPRESSIONS)}
"""
