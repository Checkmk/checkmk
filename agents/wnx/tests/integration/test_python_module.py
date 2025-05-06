#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import shutil
from pathlib import Path

import pytest

from .conftest import YieldFixture
from .utils import (
    CMK_UPDATER_CHECKMK_PY,
    CMK_UPDATER_PY,
    patch_venv_config,
    postinstall_module,
    run_agent,
    unpack_modules,
    YamlDict,
)


@pytest.fixture(name="unpack", scope="module")
def unpack_fixture(
    root_dir: Path,
    module_dir: Path,
) -> YieldFixture[None]:
    unpack_modules(root_dir, module_dir=module_dir)
    yield
    shutil.rmtree(module_dir)


def copy_cmk_updater(source_dir: Path, target_dir: Path) -> None:
    shutil.copy(source_dir / CMK_UPDATER_PY, target_dir / CMK_UPDATER_CHECKMK_PY)


def test_python_module(
    main_exe: Path,
    default_yaml_config: YamlDict,
    unpack: object,
    module_dir: Path,
    data_dir: Path,
    repo_root: Path,
) -> None:
    assert postinstall_module(module_dir) == 0
    assert (module_dir / "DLLs").exists()
    patch_venv_config(module_dir)
    exe_output = run_agent(
        default_yaml_config,
        param="updater",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert exe_output.ret_code == 1
    assert exe_output.stdout.startswith("\r\n\tYou must install Agent Updater Python plugin")
    copy_cmk_updater(
        repo_root / "non-free" / "packages" / "cmk-update-agent",
        data_dir / "plugins",
    )
    exe_output = run_agent(
        default_yaml_config,
        param="updater",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert exe_output.ret_code == 0
    assert exe_output.stderr.startswith("Missing config file")
    assert exe_output.stdout.startswith("<<<cmk_update_agent_status:sep(0)>>>")
