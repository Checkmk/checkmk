#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest  # type: ignore[import]

from testlib.base import Scenario

import cmk.utils.paths

import cmk.base.config as config
from cmk.base.config import SpecialAgentConfiguration, SpecialAgentInfoFunctionResult
from cmk.base.data_sources.programs import (
    DSProgramConfigurator,
    DSProgramDataSource,
    SpecialAgentConfigurator,
    SpecialAgentDataSource,
)

fun_args_stdin: Tuple[  #
    Tuple[SpecialAgentInfoFunctionResult, Tuple[str, Optional[str]]]  #
] = (  #
    ("arg0 arg1", "arg0 arg1", None),
    (["arg0", "arg1"], "'arg0' 'arg1'", None),
    (SpecialAgentConfiguration("arg0", None), "arg0", None),
    (SpecialAgentConfiguration("arg0 arg1", None), "arg0 arg1", None),
    (SpecialAgentConfiguration(["list0", "list1"], None), "'list0' 'list1'", None),
    (
        SpecialAgentConfiguration("arg0 arg1", "stdin_blob"),
        "arg0 arg1",
        "stdin_blob",
    ),
    (
        SpecialAgentConfiguration(["list0", "list1"], "stdin_blob"),
        "'list0' 'list1'",
        "stdin_blob",
    ),
)  # type: ignore[assignment]


class TestDSProgramDataSource:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(self, monkeypatch, ipaddress):
        template = ""
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)

        configurator = DSProgramConfigurator(
            hostname,
            ipaddress,
            template=template,
        )
        assert configurator.cmdline == ""
        assert configurator.stdin is None
        assert configurator.description == "Program: "

        source = DSProgramDataSource(configurator=configurator)
        assert source.id == "agent"
        # ProgramDataSource
        assert source._cpu_tracking_id == "ds"

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_template_translation(self, monkeypatch, ipaddress):
        template = "<NOTHING>x<IP>x<HOST>x<host>x<ip>x"
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)
        configurator = DSProgramConfigurator(hostname, ipaddress, template=template)

        assert configurator.cmdline == "<NOTHING>x%sx%sx<host>x<ip>x" % (
            ipaddress if ipaddress is not None else "",
            hostname,
        )


class TestSpecialAgentDataSource:
    @pytest.fixture(autouse=True)
    def agent_dir(self, monkeypatch):
        dir_ = Path("/tmp")
        monkeypatch.setattr(cmk.utils.paths, "local_agents_dir", dir_)
        monkeypatch.setattr(cmk.utils.paths, "agents_dir", dir_)
        return dir_

    @pytest.fixture
    def special_agent_id(self):
        return "my_id"

    @pytest.fixture(params=fun_args_stdin)
    def patch_config(self, special_agent_id, monkeypatch, request):
        fun, args, stdin = request.param
        monkeypatch.setitem(
            config.special_agent_info,
            special_agent_id,
            lambda a, b, c: fun,
        )
        return args, stdin

    @pytest.fixture
    def expected_args(self, patch_config):
        return patch_config[0]

    @pytest.fixture
    def expected_stdin(self, patch_config):
        return patch_config[1]

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(
        self,
        special_agent_id,
        ipaddress,
        agent_dir,
        expected_args,
        expected_stdin,
        monkeypatch,
    ):
        hostname = "testhost"
        params: Dict[Any, Any] = {}
        Scenario().add_host(hostname).apply(monkeypatch)

        # end of setup

        configurator = SpecialAgentConfigurator(
            hostname,
            ipaddress,
            special_agent_id=special_agent_id,
            params=params,
        )
        assert configurator.cmdline == (  #
            str(agent_dir / "special" / ("agent_%s" % special_agent_id)) + " " + expected_args)
        assert configurator.stdin == expected_stdin

        source = SpecialAgentDataSource(configurator=configurator)

        assert source.id == "special_%s" % special_agent_id

        assert source._cpu_tracking_id == "ds"
