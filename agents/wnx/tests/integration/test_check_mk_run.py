#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path
from typing import Dict, Final, List, Sequence, Union

import pytest
from utils import CTL_STATUS_LINE, obtain_agent_data, ONLY_FROM_LINE, SECTION_COUNT, YamlDict


def _make_config(config: YamlDict, only_from: Sequence[str]) -> YamlDict:
    if only_from:
        config["global"]["only_from"] = only_from
    return config


def _get_ctl_status_line(data: Sequence[str]) -> Dict[str, Union[str, List, bool]]:
    s = data[CTL_STATUS_LINE].replace(":false", ":False").replace(":true", ":True")
    return ast.literal_eval(s)


_NOT_WMI_SECTIONS: Final = {
    "<<<wmi_cpuload:sep(124)>>>",
    "<<<uptime>>>",
    "<<<mem>>>",
    "<<<df:sep(9)>>>",
    "<<<fileinfo:sep(124)>>>",
    "<<<logwatch>>>",
    "<<<checkmk_agent_plugins_win:sep(0)>>>",
    "<<<winperf_phydisk>>>",
    "<<<winperf_if>>>",
    "<<<winperf_processor>>>",
    "<<<ps:sep(9)>>>",
    "<<<services>>>",
}

_WMI_SECTIONS: Final = {
    "<<<dotnet_clrmemory:sep(124)>>>",
    "<<<wmi_webservices:sep(124)>>>",
}


_INTERNAL_SECTIONS: Final = _NOT_WMI_SECTIONS.union(_WMI_SECTIONS)


@pytest.mark.parametrize(
    "only_from, description",
    [
        ([], "default"),
        (["127.0.0.1", "::1", "10.1.2.3"], "custom"),
    ],
)
def test_check_mk_base(
    main_exe: Path,
    default_yaml_config: YamlDict,
    data_dir: Path,
    only_from: List[str],
) -> None:
    output = obtain_agent_data(
        _make_config(default_yaml_config, only_from),
        main_exe=main_exe,
        data_dir=data_dir,
    )
    # correct value of only_from also guaranties that we are using own config
    assert output[ONLY_FROM_LINE] == "OnlyFrom: " + " ".join(only_from)

    # NOTE. We validate the output only roughly: sections must be presented in correct order.
    # Full validation may be achieved only using checkmk site and this is impossible.
    # Details of a section are verified using unit-tests.
    sections = [line for line in output if line[:3] == "<<<"]
    assert sections[0] == "<<<check_mk>>>"
    assert sections[1] == "<<<cmk_agent_ctl_status:sep(0)>>>"
    assert sections.count("<<<>>>") == 2
    assert _INTERNAL_SECTIONS.issubset(
        set(sections)
    ), f"Missing sections: {_INTERNAL_SECTIONS.difference((set(sections)))}"
    assert sections[-1] == "<<<systemtime>>>"
    assert len(sections) == SECTION_COUNT

    # Validate controller status is the expected one.
    ctl_status = _get_ctl_status_line(output)
    assert isinstance(ctl_status["version"], str)
    assert ctl_status["version"].startswith("2.")
    assert ctl_status["agent_socket_operational"] is True
    assert ctl_status["ip_allowlist"] == only_from
    assert ctl_status["allow_legacy_pull"] is True
    assert ctl_status["connections"] == []


@pytest.fixture(name="config_no_wmi")
def config_no_wmi_fixture(default_yaml_config: YamlDict) -> YamlDict:
    default_yaml_config["global"]["wmi_timeout"] = 0
    return default_yaml_config


def test_check_mk_no_wmi(
    main_exe: Path,
    config_no_wmi: YamlDict,
    data_dir: Path,
):
    output = obtain_agent_data(
        config_no_wmi,
        main_exe=main_exe,
        data_dir=data_dir,
    )
    sections = [line for line in output if line[:3] == "<<<"]
    assert sections[0] == "<<<check_mk>>>"
    assert sections[1] == "<<<cmk_agent_ctl_status:sep(0)>>>"
    assert sections.count("<<<>>>") == 2
    assert len(_WMI_SECTIONS.intersection(set(sections))) == 0
    assert sections[-1] == "<<<systemtime>>>"
