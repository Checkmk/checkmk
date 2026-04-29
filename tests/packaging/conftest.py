#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest


def _resolve_packages(config: pytest.Config) -> list[Path]:
    """Return the list of packages to test, in priority order:
    1. --packages CLI option
    2. PACKAGE_PATH env var (comma-separated)
    3. Auto-discovery via _find_packages in cwd
    """
    packages: list[str] | None = config.getoption("--packages")
    if packages:
        return [Path(p).expanduser().resolve() for p in packages]
    env_paths = os.environ.get("PACKAGE_PATH", "")
    if env_paths:
        return [Path(p.strip()).expanduser().resolve() for p in env_paths.split(",") if p.strip()]
    raise RuntimeError(
        "PACKAGE_PATH environment variable pointing to the package to be tested is missing"
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("package-sanity", "Package sanity test options")
    group.addoption(
        "--packages",
        nargs="*",
        default=None,
        metavar="PACKAGE",
        help=(
            "CMK package file(s) to test. "
            "Falls back to PACKAGE_PATH env var (comma-separated) or auto-discovery in cwd."
        ),
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "package_path" not in metafunc.fixturenames:
        return
    paths = _resolve_packages(metafunc.config)
    metafunc.parametrize(
        "package_path",
        [str(p) for p in paths],
        ids=[p.name for p in paths],
        scope="module",
    )
