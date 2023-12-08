#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.agent_based_api.v1 import (  # pylint: disable=cmk-module-layer-violation
    render,
)


def message_if_rebot_is_too_old(
    *,
    rebot_timestamp: int,
    execution_interval: int,
    now: float,
) -> str | None:
    if (rebot_age := now - rebot_timestamp) > 2 * execution_interval:
        return (
            f"Data is too old (age: {render.timespan(rebot_age)}, "
            f"execution interval: {render.timespan(execution_interval)})"
        )
    return None
