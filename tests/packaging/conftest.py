#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest

from tests.testlib import package_manager
from tests.testlib.utils import version_spec_from_env


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--package-path",
        action="store",
        help=(
            "Path to the package file to test "
            "(e.g., check-mk-enterprise-2.4.0p13_0.noble_amd64.deb). "
            "This is a helper for local execution of packaging tests, as CI uses the env."
        ),
    )


@pytest.fixture(scope="session", autouse=True)
def _configure_environment_from_package_path(request: pytest.FixtureRequest) -> None:
    """Auto-configure environment variables from --package-path option."""
    package_path_opt = request.config.getoption("--package-path")

    if package_path_opt:
        # Expand user path and resolve to absolute path
        abs_path = str(Path(package_path_opt).expanduser().resolve())
        os.environ["PACKAGE_PATH"] = abs_path

        # Extract and set VERSION (always override to ensure consistency with package path)
        package_info = package_manager.package_info_from_path(Path(abs_path))
        os.environ["VERSION"] = package_info.version.version


# TODO: Better hand over arguments using pytest mechanisms
#       (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def package_path() -> str:
    path = os.environ.get("PACKAGE_PATH")
    if not path:
        raise Exception(
            "PACKAGE_PATH environment variable pointing to the package to be tested is missing"
        )
    return path


# TODO: Better hand over arguments using pytest mechanisms
#       (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def cmk_version() -> str:
    return version_spec_from_env()
