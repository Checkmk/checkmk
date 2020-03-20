#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.utils.paths
from cmk.base.data_sources.programs import (
    DSProgramDataSource,
    SpecialAgentConfiguration,
    SpecialAgentDataSource,
)
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


class TestDSProgramDataSource:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(self, monkeypatch, ipaddress):
        template = ""
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)
        source = DSProgramDataSource(hostname, ipaddress, template)

        assert source.id() == "agent"
        assert source.name() == ""
        # ProgramDataSource
        assert source._cpu_tracking_id() == "ds"
        assert source._get_command_line_and_stdin() == ("", None)
        assert source.describe() == "Program: "

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_translate_legacy_macro(self, monkeypatch, ipaddress):
        template = "<NOTHING>x<IP>x<HOST>x<host>x<ip>x"
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)
        source = DSProgramDataSource(hostname, ipaddress, template)

        assert source._translate_legacy_macros(template) == "<NOTHING>x%sx%sx<host>x<ip>x" % (
            ipaddress if ipaddress is not None else "", hostname)


class TestSpecialAgentDataSource:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(self, monkeypatch, ipaddress):
        id = "my_id"
        hostname = "testhost"
        params = {}
        Scenario().add_host(hostname).apply(monkeypatch)
        source = SpecialAgentDataSource(hostname, ipaddress, id, params)

        assert source.id() == "special_%s" % id
        # ProgramDataSource
        assert source._cpu_tracking_id() == "ds"

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_unconfigured_get_command_line_and_stdin_raise_KeyError(self, monkeypatch, ipaddress):
        id = "my_id"
        hostname = "testhost"
        params = {}
        Scenario().add_host(hostname).apply(monkeypatch)
        source = SpecialAgentDataSource(hostname, ipaddress, id, params)

        # TODO(ml): Does this make sense?
        with pytest.raises(KeyError):
            source._get_command_line_and_stdin()

        with pytest.raises(KeyError):
            source.describe()
