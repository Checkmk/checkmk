#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from pathlib import Path
from typing import Final, Generator, TypeVar

import pytest
import yaml
from utils import (
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
  logging:
    debug: true
  wmi_timeout: 10
  port: {}
"""

_TEST_ENV_VAR: Final = "WNX_INTEGRATION_BASE_DIR"  # supplied by script
_ARTIFACTS_ENV_VAR: Final = "arte"  # supplied by script
_FACTORY_YAML_CONFIG: Final = "check_mk.yml"
_CTL_EXE_NAME: Final = "cmk-agent-ctl.exe"


@pytest.fixture(name="artifacts_dir", scope="session")
def artifacts_dir_fixture() -> Path:
    p = get_path_from_env(_ARTIFACTS_ENV_VAR)
    assert p.exists()
    return p


@pytest.fixture(name="main_dir", scope="session")
def main_dir_fixture() -> Path:
    return get_path_from_env(_TEST_ENV_VAR)


@pytest.fixture(name="data_dir", scope="session")
def data_dir_fixture(main_dir: Path) -> Path:
    return main_dir / "test" / "data"


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
def setup_all(
    main_dir: Path,
    data_dir: Path,
    artifacts_dir: Path,
    root_dir: Path,
) -> YieldFixture[None]:
    shutil.rmtree(main_dir, ignore_errors=True)
    os.makedirs(root_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(data_dir / "bin", exist_ok=True)
    os.makedirs(data_dir / "log", exist_ok=True)
    for f in [_FACTORY_YAML_CONFIG, AGENT_EXE_NAME, _CTL_EXE_NAME]:
        shutil.copy(artifacts_dir / f, root_dir)
    create_protocol_file(data_dir)
    create_legacy_pull_file(data_dir)
    yield
