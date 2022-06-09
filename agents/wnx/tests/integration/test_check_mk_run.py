#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, List

import pytest
from utils import obtain_agent_data, ONLY_FROM_LINE, SECTION_COUNT, YamlDict


def _make_config(config: YamlDict, only_from: List[str]) -> YamlDict:
    if only_from:
        config["global"]["only_from"] = only_from
    return config


_INTERNAL_SECTIONS: Final = {
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
    "<<<dotnet_clrmemory:sep(124)>>>",
    "<<<wmi_webservices:sep(124)>>>",
}


@pytest.mark.parametrize(
    "only_from",
    [
        ([]),
        (["127.0.0.1", "::1", "10.1.2.3"]),
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
