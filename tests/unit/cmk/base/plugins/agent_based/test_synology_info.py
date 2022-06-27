# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based import synology_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State

SECTION_TABLE = [["DS218", "19A0QEN742405", "DSM 7.0-42218"]]


def test_parsing() -> None:
    section = synology_info.parse(SECTION_TABLE)
    assert section == synology_info.Section(
        model="DS218", serialnumber="19A0QEN742405", os="DSM 7.0-42218"
    )


def test_discovery() -> None:
    section = synology_info.parse(SECTION_TABLE)
    assert section is not None
    services = list(synology_info.discovery(section))
    assert len(services) == 1


def test_result_state() -> None:
    section = synology_info.parse(SECTION_TABLE)
    assert section is not None
    result = list(synology_info.check(section=section))[0]
    assert isinstance(result, Result)
    assert result.state == State.OK
    assert result.summary == "Model: DS218, S/N: 19A0QEN742405, OS Version: DSM 7.0-42218"
