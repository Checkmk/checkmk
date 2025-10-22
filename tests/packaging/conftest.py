#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

import pytest

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


def _extract_version_from_package_path(package_file_path: str) -> str:
    """Extract version from package filename.

    Examples:
        check-mk-enterprise-2.3.0p39_0.noble_amd64.deb -> 2.3.0p39
        check-mk-enterprise-2.3.0-2025.10.27-el9-38.x86_64.rpm -> 2.3.0-2025.10.27
        check-mk-enterprise-2.3.0-2025.10.27-4-x86_64.cma -> 2.3.0-2025.10.27
        check-mk-enterprise-2.3.0-2025.10.27.cee.tar.gz -> 2.3.0-2025.10.27
    """
    basename = Path(package_file_path).name

    # For 2.3.0 versions: extract version starting with "2.3.0" until first _ or distro marker
    match = re.search(
        r"-(2\.3\.0[^_]*?)(?:_|-(?:el|sles)\d+|-\d+-|\.(?:cee|cre|cme|cce|cse|tar))", basename
    )
    if not match:
        # Fallback: version at end before extension
        match = re.search(r"-(2\.3\.0[^_.]+)", basename)

    if not match:
        raise ValueError(f"Could not extract version from package path: {package_file_path}")

    return match.group(1)


@pytest.fixture(scope="session", autouse=True)
def _configure_environment_from_package_path(request: pytest.FixtureRequest) -> None:
    """Auto-configure environment variables from --package-path option."""
    package_path_opt = request.config.getoption("--package-path")

    if package_path_opt:
        # Expand user path and resolve to absolute path
        abs_path = str(Path(package_path_opt).expanduser().resolve())
        os.environ["PACKAGE_PATH"] = abs_path

        # Extract and set VERSION (always override to ensure consistency with package path)
        # note:   from 2.4.0 on we have package_manager available, in 2.3.0 we don't
        #         for simplicity we use the regex here.
        version = _extract_version_from_package_path(package_path_opt)
        os.environ["VERSION"] = version


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
