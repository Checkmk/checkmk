#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator
from pathlib import Path
from typing import Final, TypeVar

import pytest
import yaml

from .utils import (
    AGENT_EXE_NAME,
    check_os,
    create_legacy_pull_file,
    create_protocol_file,
    get_path_from_env,
    INTEGRATION_PORT,
    YamlDict,
)

T = TypeVar("T")
YieldFixture = Generator[T, None, None]


check_os()

_DEFAULT_CONFIG: Final = """
global:
  enabled: true
  disabled_sections: wmi_webservices
  logging:
    debug: true
  wmi_timeout: 10
  port: {}
"""


_REPO_ROOT_ENV_VAR: Final = "repo_root"  # supplied by script


@pytest.fixture(name="repo_root", scope="session")
def repo_root_fixture() -> Path:
    return get_path_from_env(_REPO_ROOT_ENV_VAR)


_TEST_ENV_VAR: Final = "WNX_INTEGRATION_BASE_DIR"  # supplied by script


@pytest.fixture(name="main_dir", scope="session")
def main_dir_fixture() -> Path:
    return get_path_from_env(_TEST_ENV_VAR)


@pytest.fixture(name="data_dir", scope="session")
def data_dir_fixture(main_dir: Path) -> Path:
    return main_dir / "test" / "data"


@pytest.fixture(name="module_dir", scope="session")
def module_dir_fixture(data_dir: Path) -> Path:
    return data_dir / "modules" / "python-3"


@pytest.fixture(name="root_dir", scope="session")
def root_dir_fixture(main_dir: Path) -> Path:
    return main_dir / "test" / "root"


@pytest.fixture(name="main_exe", scope="session")
def main_exe_fixture(root_dir: Path) -> Path:
    return root_dir / AGENT_EXE_NAME


@pytest.fixture(name="default_yaml_config", scope="session")
def default_yaml_config_fixture() -> YamlDict:
    return yaml.safe_load(_DEFAULT_CONFIG.format(INTEGRATION_PORT))


@pytest.fixture(autouse=True, scope="session")
def setup_all(data_dir: Path) -> YieldFixture[None]:
    create_protocol_file(data_dir)
    create_legacy_pull_file(data_dir)
    yield
