#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Iterable, Mapping, Optional

# The only reasonable thing to do here is use our own version parsing. It's to big to duplicate.
from cmk.utils.version import parse_check_mk_version  # pylint: disable=cmk-module-layer-violation

from .agent_based_api.v1 import check_levels, regex, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.checkmk import CheckmkSection, Plugin, PluginSection


def discover_checkmk_agent(
    section_check_mk: Optional[CheckmkSection],
    section_checkmk_agent_plugins: Optional[PluginSection],
) -> DiscoveryResult:
    # If we're called, at least one section is not None, so just disocver.
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


def _check_cmk_agent_update(params: Mapping[str, Any], section: CheckmkSection) -> CheckResult:
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
        # Note: Transformation of URLs from this check (check_mk-check_mk_agent) to icons
        # is disabled explicitly in cmk.gui.view_utils:format_plugin_output
        yield Result(state=State.OK, summary=f"Update URL: {update_url}")

    if aghash := parsed.get("aghash"):
        yield Result(state=State.OK, summary=f"Agent configuration: {aghash[:8]}")

    if pending := parsed.get("pending_hash"):
        yield Result(state=State.OK, summary=f"Pending installation: {pending[:8]}")

    return


def _check_checkmk_agent_plugins(params: Mapping[str, Any], section: PluginSection) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Agent plugins: {len(section.plugins)}",
    )
    yield Result(
        state=State.OK,
        summary=f"Local checks: {len(section.local_checks)}",
    )

    if (min_versions := params.get("min_versions")) is None:
        return

    if (exclude_pattern := params.get("exclude_pattern")) is None:
        plugins = section.plugins
        lchecks = section.local_checks
    else:
        comp = regex(exclude_pattern)
        plugins = [p for p in section.plugins if not comp.search(p.name)]
        lchecks = [p for p in section.local_checks if not comp.search(p.name)]

    yield from _check_min_version(plugins, min_versions, "Agent plugin")
    yield from _check_min_version(lchecks, min_versions, "Local check")


def _check_min_version(
    plugins: Iterable[Plugin], levels_str: tuple[str, str], type_: str
) -> Iterable[Result]:
    levels = (parse_check_mk_version(levels_str[0]), parse_check_mk_version(levels_str[1]))

    render_info = {p.version_int: p.version for p in plugins}
    render_info.update(zip(levels, levels_str))

    for plugin in plugins:
        if plugin.version_int is None:
            yield Result(
                state=State.UNKNOWN,
                summary=f"{type_} {plugin.name!r}: unable to parse version {plugin.version!r}",
            )
        else:
            (result,) = check_levels(
                plugin.version_int,
                levels_lower=levels,
                render_func=lambda v: render_info[int(v)],
                label=f"{type_} {plugin.name!r}",
            )
            if result.state is not State.OK:
                yield result


def check_checkmk_agent(
    params: Mapping[str, Any],
    section_check_mk: Optional[CheckmkSection],
    section_checkmk_agent_plugins: Optional[PluginSection],
) -> CheckResult:
    if section_check_mk is not None:
        yield from _check_cmk_agent_update(params, section_check_mk)

    if section_checkmk_agent_plugins is not None:
        yield from _check_checkmk_agent_plugins(params, section_checkmk_agent_plugins)


register.check_plugin(
    name="checkmk_agent",
    service_name="Check_MK Agent",
    sections=["check_mk", "checkmk_agent_plugins"],
    discovery_function=discover_checkmk_agent,
    check_function=check_checkmk_agent,
    # TODO: rename the ruleset?
    check_ruleset_name="agent_update",
    check_default_parameters={},
)
