#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import shutil
from pathlib import Path

import pytest
from conftest import YieldFixture
from utils import (
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
    unpack,
    module_dir: Path,
    data_dir: Path,
    git_dir: Path,
) -> None:

    assert not (module_dir / "DLLs").exists()
    assert postinstall_module(module_dir) == 0
    assert (module_dir / "DLLs").exists()
    patch_venv_config(module_dir)
    output = run_agent(
        default_yaml_config,
        param="updater",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert output.ret_code == 1
    assert output.stdout.startswith("\r\n\tYou must install Agent Updater Python plugin")
    copy_cmk_updater(
        git_dir / "enterprise" / "agents" / "plugins",
        data_dir / "plugins",
    )
    output = run_agent(
        default_yaml_config,
        param="updater",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert output.ret_code == 0
    assert output.stderr.startswith("Missing config file")
    assert output.stdout.startswith("<<<check_mk>>>")
