#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest

from .utils import run_agent, YamlDict


def test_check_mk_agent_cmd_line_help(
    main_exe: Path,
    default_yaml_config: YamlDict,
    data_dir: Path,
) -> None:
    output = run_agent(
        default_yaml_config,
        param="help",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert output.ret_code == 0
    assert output.stderr == ""
    assert output.stdout.startswith("Normal Usage:")
    assert 100 > len(output.stdout.split("\r\n")) > 50


def _splitter(line: str) -> dict[str, str]:
    l = line.split("DIR=")
    return {l[0]: l[1]}


_ENV_MAP: Final = {
    "MK_LOCALDIR": "local",
    "MK_STATEDIR": "state",
    "MK_PLUGINSDIR": "plugins",
    "MK_TEMPDIR": "tmp",
    "MK_LOGDIR": "log",
    "MK_CONFDIR": "config",
    "MK_SPOOLDIR": "spool",
    "MK_INSTALLDIR": "install",
    "MK_MSI_PATH": "update",
    "MK_MODULESDIR": "modules",
}


def test_check_mk_agent_cmd_line_show_config(
    main_exe: Path,
    default_yaml_config: YamlDict,
    data_dir: Path,
) -> None:
    output = run_agent(
        default_yaml_config,
        param="showconfig",
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert output.ret_code == 0
    assert output.stderr == ""
    assert output.stdout.startswith("# Environment Variables:")
    result = output.stdout.split("\r\n")
    assert 200 > len(result) > 100
    r = set(result)
    assert {"  disabled_sections: wmi_webservices", "  port: 25998"}.issubset(r)

    envs_set = {l[2:] for l in result if l.startswith("# MK_")}
    envs = {p[0]: p[1] for p in list(map(lambda x: x.split("="), envs_set))}
    for k, v in _ENV_MAP.items():
        assert envs[k] == f'"{str(data_dir / v)}"'


@pytest.mark.parametrize(
    "command, code, starts_with",
    [
        ("trash", 13, 'Provided Parameter "trash" is not allowed'),
        ("updater", 1, "\r\n\tYou must install Agent Updater Python plugin to use the updater"),
    ],
)
def test_check_mk_agent_cmd_line_bad(
    main_exe: Path,
    default_yaml_config: YamlDict,
    data_dir: Path,
    command: str,
    code: int,
    starts_with: str,
) -> None:
    output = run_agent(
        default_yaml_config,
        param=command,
        main_exe=main_exe,
        data_dir=data_dir,
    )
    assert output.ret_code == code
    assert output.stderr == ""
    assert output.stdout.startswith(starts_with)
