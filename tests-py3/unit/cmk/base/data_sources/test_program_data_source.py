#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Optional, Tuple

import pytest  # type: ignore[import]

import cmk.base.config as config
from cmk.base.config import SpecialAgentConfiguration, SpecialAgentInfoFunctionResult
import cmk.utils.paths
from cmk.base.data_sources.programs import (
    DSProgramDataSource,
    SpecialAgentDataSource,
)
from testlib.base import Scenario

info_func_result_and_expected: List[Tuple[SpecialAgentInfoFunctionResult,
                                          Tuple[str, Optional[str]]]] = [
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
                                                  SpecialAgentConfiguration(["list0", "list1"],
                                                                            None),
                                                  ("'list0' 'list1'", None),
                                              ),
                                              (
                                                  SpecialAgentConfiguration(
                                                      "arg0 arg1", "stdin_blob"),
                                                  ("arg0 arg1", "stdin_blob"),
                                              ),
                                              (
                                                  SpecialAgentConfiguration(["list0", "list1"],
                                                                            "stdin_blob"),
                                                  ("'list0' 'list1'", "stdin_blob"),
                                              ),
                                          ]


@pytest.mark.parametrize("info_func_result,expected", info_func_result_and_expected)
def test_command_line_and_stdin(monkeypatch, info_func_result, expected):
    Scenario().add_host("testhost").apply(monkeypatch)
    special_agent_id = "bi"
    agent_prefix = "%s/special/agent_%s " % (cmk.utils.paths.agents_dir, special_agent_id)
    ds = SpecialAgentDataSource("testhost", "127.0.0.1", special_agent_id, {})
    monkeypatch.setattr(config, "special_agent_info",
                        {special_agent_id: lambda a, b, c: info_func_result})

    assert ds.source_cmdline == agent_prefix + expected[0]
    assert ds.source_stdin == expected[1]


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
        assert source.source_cmdline == ""
        assert source.source_stdin is None
        assert source.describe() == "Program: "

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_template_translation(self, monkeypatch, ipaddress):
        template = "<NOTHING>x<IP>x<HOST>x<host>x<ip>x"
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)
        source = DSProgramDataSource(hostname, ipaddress, template)

        assert source.source_cmdline == "<NOTHING>x%sx%sx<host>x<ip>x" % (
            ipaddress if ipaddress is not None else "", hostname)


class TestSpecialAgentDataSource:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(self, monkeypatch, ipaddress):
        the_id = "my_id"
        hostname = "testhost"
        params: Dict[Any, Any] = {}
        Scenario().add_host(hostname).apply(monkeypatch)
        source = SpecialAgentDataSource(hostname, ipaddress, the_id, params)

        assert source.id() == "special_%s" % the_id
        # ProgramDataSource
        assert source._cpu_tracking_id() == "ds"

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_unconfigured_command_line_raise_KeyError(self, monkeypatch, ipaddress):
        the_id = "my_id"
        hostname = "testhost"
        params: Dict[Any, Any] = {}
        Scenario().add_host(hostname).apply(monkeypatch)
        source = SpecialAgentDataSource(hostname, ipaddress, the_id, params)

        # TODO(ml): Does this make sense?
        with pytest.raises(KeyError):
            # pyflake people are highly ignorant regarding common practice...
            # :-P See https://github.com/PyCQA/pyflakes/issues/393
            _ignore_me = source.source_cmdline  # noqa: F841

        with pytest.raises(KeyError):
            source.describe()
