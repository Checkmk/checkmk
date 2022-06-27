#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import os

import pytest
import vcr  # type: ignore[import]

from cmk.special_agents import agent_innovaphone


@pytest.mark.parametrize(
    "args, expected_stdout",
    [
        (
            [
                "192.168.178.10",
                "USER",
                "PASSWORD",
            ],
            "<<<innovaphone_cpu>>>\nCPU 21\n<<<innovaphone_mem>>>\nMEM 5\n<<<innovaphone_temp>>>\nTEMP 35\n<<<innovaphone_channels>>>\nPRI1 Up Up 8 30\nPRI2 Up Up 12 30\n<<<innovaphone_licenses>>>\n",
        )
    ],
)
def test_agent_innovaphone_main(args, expected_stdout, capsys) -> None:
    filepath = "%s/_innovaphone_vcrtrace" % os.path.dirname(os.path.abspath(__file__))
    with vcr.use_cassette(filepath, record_mode="none"):
        agent_innovaphone.main(args)
        assert expected_stdout == capsys.readouterr().out
