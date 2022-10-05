#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cmk.utils.type_defs import HostAddress, HostName

import cmk.core_helpers.cache as file_cache

from cmk.base.sources.programs import DSProgramSource


class TestDSProgramChecker:
    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_attribute_defaults(self, ipaddress: HostAddress | None) -> None:
        hostname = HostName("testhost")
        source = DSProgramSource(
            hostname,
            ipaddress,
            id_="agent",
            persisted_section_dir=Path(os.devnull),
            cache_dir=Path(os.devnull),
            cmdline="",
            stdin=None,
            simulation_mode=True,
            agent_simulator=True,
            translation={},
            encoding_fallback="ascii",
            check_interval=0,
            is_cmc=False,
            file_cache_max_age=file_cache.MaxAge.none(),
        )
        # Only check the computed attributes.
        assert source.id == "agent"
