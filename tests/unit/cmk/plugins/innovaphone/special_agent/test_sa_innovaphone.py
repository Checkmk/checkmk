#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from collections.abc import Sequence

import pytest
import vcr  # type: ignore[import-untyped,unused-ignore]

from cmk.plugins.innovaphone.special_agent import agent_innovaphone


@pytest.mark.parametrize(
    "args, expected_stdout",
    [
        (
            [
                "192.168.178.10",
                "--user",
                "USER",
                "--password",
                "PASSWORD",
            ],
            "<<<innovaphone_cpu>>>\nCPU 21\n<<<innovaphone_mem>>>\nMEM 5\n<<<innovaphone_temp>>>\nTEMP 35\n<<<innovaphone_channels>>>\nPRI1 Up Up 8 30\nPRI2 Up Up 12 30\n<<<innovaphone_licenses>>>\n",
        )
    ],
)
def test_agent_innovaphone_main(
    args: Sequence[str], expected_stdout: str, capsys: pytest.CaptureFixture[str]
) -> None:
    filepath = "%s/innovaphone_vcrtrace.yaml" % os.path.dirname(__file__)
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        filepath,
        record_mode="none",
    ):
        agent_innovaphone.main(args)
        assert expected_stdout == capsys.readouterr().out
