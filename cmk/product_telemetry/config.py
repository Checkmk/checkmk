#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.base.config import load


@dataclass
class TelemetryEnabledConfig:
    enabled: bool


def telemetry_enabled_config() -> TelemetryEnabledConfig:
    config = load({})

    return TelemetryEnabledConfig(
        enabled=config.loaded_config.product_telemetry.get("enable_telemetry")[0] == "enabled"
    )
