#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Error, Hook, null_action

from cmk.flags import load_release_flags


def ai_agent_engine_has_error(value: str) -> None | Error:
    if value not in ("on", "off"):
        return Error("Allowed are: on, off")
    if value == "on" and not load_release_flags(Path("etc/check_mk")).exp_ai_assistant:
        return Error("This experimental testing feature is not enabled.")
    return None


AI_AGENT_ENGINE = Hook(
    name="AI_AGENT_ENGINE",
    default=lambda _edition: "off",
    activation=null_action,
    choices=ai_agent_engine_has_error,
)
