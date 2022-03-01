#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

# TODO: find a solution for the duplicate code in the check section parsing.
Section = Mapping[str, str]


def discover_cmk_agent_update(section: Section) -> DiscoveryResult:
    if "agentupdate" in section:
        yield Service()


def _get_error_result(error: str, params: Mapping[str, Any]) -> CheckResult:
    # Sometimes we get duplicate output. Until we find out why, fix the error message:
    if "last_check" in error and "last_update" in error and "error" in error:
        error = error.split("error", 1)[1].strip()

    if error == "None" or not error:
        return

    default_state = State.WARN
    if "deployment is currently globally disabled" in error:
        yield Result(
            state=State(params.get("error_deployment_globally_disabled", default_state)),
            summary=error,
        )
    else:
        yield Result(state=default_state, summary=f"Error: {error}")


def check_cmk_agent_update(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (raw_string := section.get("agentupdate")):
        return

    if "error" in raw_string:
        non_error_part, error = raw_string.split("error", 1)
        yield from _get_error_result(error.strip(), params)
    else:
        non_error_part = raw_string

    parts = iter(non_error_part.split())
    parsed = {k: v for k, v in zip(parts, parts) if v != "None"}

    try:
        last_check = float(parsed.get("last_check", ""))
    except ValueError:
        yield Result(state=State.WARN, summary="No successful connect to server yet")
    else:
        yield from check_levels(
            time.time() - last_check,
            levels_upper=(2 * 3600 * 24, None),  # type: ignore[arg-type]
            render_func=render.timespan,
            label="Time since last update check",
            notice_only=True,
        )
        yield Result(state=State.OK, summary=f"Last update check: {render.datetime(last_check)}")

    if last_update := parsed.get("last_update"):
        yield Result(
            state=State.OK,
            summary=f"Last agent update: {render.datetime(float(last_update))}",
        )

    if update_url := parsed.get("update_url"):
        # Note: Transformation of URLs from this check (check_mk-check_mk_agent_update) to icons
        # is disabled explicitly in cmk.gui.view_utils:format_plugin_output
        yield Result(state=State.OK, summary=f"Update URL: {update_url}")

    if aghash := parsed.get("aghash"):
        yield Result(state=State.OK, summary=f"Agent configuration: {aghash[:8]}")

    if pending := parsed.get("pending_hash"):
        yield Result(state=State.OK, summary=f"Pending installation: {pending[:8]}")

    return


register.check_plugin(
    name="check_mk_agent_update",
    sections=["check_mk"],
    discovery_function=discover_cmk_agent_update,
    check_function=check_cmk_agent_update,
    check_ruleset_name="agent_update",
    check_default_parameters={},
    service_name="Check_MK Agent",
)
