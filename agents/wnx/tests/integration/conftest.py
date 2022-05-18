#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final, Generator, List

import pytest
import yaml
from utils import (
    check_os,
    create_protocol_file,
    get_data_from_agent,
    get_path_from_env,
    YamlDict,
    YieldFixture,
)

check_os()

_DEFAULT_CONFIG: Final = """
global:
  enabled: true
  logging:
    debug: true
  port: {}
"""

_INTEGRATION_PORT: Final = 25999
_HOST: Final = "localhost"
_TEST_ENV_VAR: Final = "WNX_INTEGRATION_BASE_DIR"  # supplied by script
_ARTIFACTS_ENV_VAR: Final = "arte"  # supplied by script
_USER_YAML_CONFIG: Final = "check_mk.user.yml"
_FACTORY_YAML_CONFIG: Final = "check_mk.yml"
_AGENT_EXE_NAME: Final = "check_mk_agent.exe"
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
    return root_dir / _AGENT_EXE_NAME


@pytest.fixture(name="default_yaml_config", scope="session")
def default_yaml_config_fixture() -> YamlDict:
    return yaml.safe_load(_DEFAULT_CONFIG.format(_INTEGRATION_PORT))


@pytest.fixture(autouse=True, scope="session")
def setup_all(
    main_dir: Path,
    data_dir: Path,
    artifacts_dir: Path,
    root_dir: Path,
) -> YieldFixture[None]:
    shutil.rmtree(main_dir, ignore_errors=True)
    os.makedirs(root_dir)
    os.makedirs(data_dir)
    os.makedirs(data_dir / "bin")
    os.makedirs(data_dir / "log")
    for f in [_FACTORY_YAML_CONFIG, _AGENT_EXE_NAME, _CTL_EXE_NAME]:
        shutil.copy(artifacts_dir / f, root_dir)
    create_protocol_file(data_dir)
    yield
    shutil.rmtree(main_dir, ignore_errors=True)


@pytest.fixture(name="write_config")
def write_config_fixture(work_config: YamlDict, data_dir: Path) -> YieldFixture[None]:
    yaml_file = data_dir / _USER_YAML_CONFIG
    with open(yaml_file, "wt") as f:
        ret = yaml.dump(work_config)
        f.write(ret)
    yield
    yaml_file.unlink()


@pytest.fixture(name="obtain_output")
def obtain_output_fixture(
    main_exe: Path,
    write_config: Generator[None, None, None],
) -> YieldFixture[List[str]]:
    with subprocess.Popen(
        [main_exe, "exec", "-integration"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as p:
        yield get_data_from_agent(_HOST, _INTEGRATION_PORT)
        p.terminate()
        # hammer kill of the process, terminate may be too long
        subprocess.call(f'taskkill /F /FI "pid eq {p.pid}" /FI "IMAGENAME eq {_AGENT_EXE_NAME}"')
