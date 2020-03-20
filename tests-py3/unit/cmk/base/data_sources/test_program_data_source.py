#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.utils.paths
from cmk.base.data_sources.programs import SpecialAgentConfiguration, SpecialAgentDataSource
from testlib.base import Scenario


@pytest.mark.parametrize("info_func_result,expected", [
    (
        "arg0 arg1",
        ("arg0 arg1", None),
    ),
    (
        ["arg0", "arg1"],
        ("'arg0' 'arg1'", None),
    ),
    (
        SpecialAgentConfiguration("arg0", None),
        ("arg0", None),
    ),
    (
        SpecialAgentConfiguration("arg0 arg1", None),
        ("arg0 arg1", None),
    ),
    (
        SpecialAgentConfiguration(["list0", "list1"], None),
        ("'list0' 'list1'", None),
    ),
    (
        SpecialAgentConfiguration("arg0 arg1", "stdin_blob"),
        ("arg0 arg1", "stdin_blob"),
    ),
    (
        SpecialAgentConfiguration(["list0", "list1"], "stdin_blob"),
        ("'list0' 'list1'", "stdin_blob"),
    ),
])
def test_get_command_line_and_stdin(monkeypatch, info_func_result, expected):
    Scenario().add_host("testhost").apply(monkeypatch)
    special_agent_id = "bi"
    agent_prefix = "%s/special/agent_%s " % (cmk.utils.paths.agents_dir, special_agent_id)
    ds = SpecialAgentDataSource("testhost", "127.0.0.1", special_agent_id, None)
    monkeypatch.setattr(config, "special_agent_info",
                        {special_agent_id: lambda a, b, c: info_func_result})
    command_line, command_stdin = ds._get_command_line_and_stdin()
    assert command_line == agent_prefix + expected[0]
    assert command_stdin == expected[1]
