#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
import vcr

from cmk.plugins.innovaphone.special_agent import agent_innovaphone


def test_agent_innovaphone_vcrtrace(capsys: pytest.CaptureFixture[str]) -> None:
    cassette_path = Path(__file__).parent / "innovaphone_vcrtrace.yaml"
    with vcr.use_cassette(cassette_path, record_mode="none"):  # type: ignore[no-untyped-call]
        agent_innovaphone.main(["192.168.178.10", "--user", "USER", "--password", "PASSWORD"])

    value = capsys.readouterr().out
    expected = """\
<<<innovaphone_cpu>>>
CPU 21
<<<innovaphone_mem>>>
MEM 5
<<<innovaphone_temp>>>
TEMP 35
<<<innovaphone_channels>>>
PRI1 Up Up 8 30
PRI2 Up Up 12 30
<<<innovaphone_licenses>>>
"""

    assert value == expected
