#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.type_defs import HostName

import cmk.base.config as config
from cmk.base.sources.programs import DSProgramSource


class TestDSProgramChecker:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(  # type:ignore[no-untyped-def]
        self, ipaddress, monkeypatch
    ) -> None:
        hostname = HostName("testhost")
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)

        source = DSProgramSource(
            config.HostConfig.make_host_config(hostname),
            ipaddress,
            cmdline="",
            simulation_mode=True,
            agent_simulator=True,
            translation={},
            encoding_fallback="ascii",
        )
        assert source.host_config.hostname == hostname
        assert source.ipaddress == ipaddress
        assert source.cmdline == ""
        assert source.stdin is None
        assert source.description == "Program: "
        assert source.id == "agent"
