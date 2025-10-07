#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.relay_protocols.configuration import EngineConfig, UserEngineConfig


class TestEngingeConfig:
    def test_from_user_engine_config(self) -> None:
        uec = UserEngineConfig(num_fetchers=0, hosts=())
        _ = EngineConfig.model_validate_json(uec.model_dump_json())
