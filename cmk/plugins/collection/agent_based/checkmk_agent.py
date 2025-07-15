#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, UTC
from typing import Any

# The only reasonable thing to do here is use our own version parsing. It's to big to duplicate.
from cmk.ccc.version import (  # pylint: disable=cmk-module-layer-violation
    __version__,
    parse_check_mk_version,
)

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.checkmk import (
    CachedPlugin,
    CachedPluginsSection,
    CheckmkSection,
    CMKAgentUpdateSection,
    ControllerSection,
    Plugin,
    PluginSection,
    render_plugin_type,
)


def _expand_curly_address_notation(ip_addresses: str | Sequence[str]) -> list[str]:
    """Expand 10.0.0.{1,2,3}.

    >>> _expand_curly_address_notation("1.1.1.1")
    ['1.1.1.1']

    >>> _expand_curly_address_notation("1.1.1.{1,3}")
    ['1.1.1.1', '1.1.1.3']

    We ignore certain stuff, this is just showing that this does not really validate anything
    This behavior is IMHO not important

    >>> _expand_curly_address_notation("1.1.1.1/1337")
    ['1.1.1.1/1337']
    """
    if isinstance(ip_addresses, str):
        ip_addresses = ip_addresses.split()

    expanded = [word for word in ip_addresses if "{" not in word]
    for word in ip_addresses:
        if word in expanded:
            continue

        prefix, tmp = word.split("{")
        curly, suffix = tmp.split("}")
        expanded.extend(f"{prefix}{i}{suffix}" for i in curly.split(","))

    return expanded


# Works with Checkmk version (without tailing .cee and/or .demo)
def _is_daily_build_version(v: str) -> bool:
    return len(v) == 10 or "-" in v


def discover_checkmk_agent(
    section_check_mk: CheckmkSection | None,
    section_checkmk_agent_plugins: PluginSection | None,
    section_cmk_agent_ctl_status: ControllerSection | None,
    section_cmk_update_agent_status: CMKAgentUpdateSection | None,
    section_checkmk_cached_plugins: CachedPluginsSection | None,
) -> DiscoveryResult:
    # If we're called, at least one section is not None, so just disocver.
    yield Service()


def _check_cmk_agent_installation(
    params: Mapping[str, Any],
    agent_info: CheckmkSection,
    controller_info: ControllerSection | None,
) -> CheckResult:
    yield from _check_version(
        agent_info.get("version"),
        __version__,
        params["agent_version"],
        State(params["agent_version_missmatch"]),
    )
    if agent_info["agentos"] is not None:
        yield Result(state=State.OK, summary="OS: %s" % agent_info["agentos"])

    yield from _check_transport(
        bool(agent_info.get("sshclient")),
        controller_info,
        State(params["legacy_pull_mode"]),
    )
    yield from _check_only_from(
        agent_info.get("onlyfrom") if controller_info is None else controller_info.ip_allowlist,
        params["only_from"],
        State(params["restricted_address_mismatch"]),
    )
    yield from _check_agent_update(
        agent_info.get("updatefailed"), agent_info.get("updaterecoveraction")
    )
    yield from _check_python_plugins(
        agent_info.get("failedpythonplugins"), agent_info.get("failedpythonreason")
    )
    yield from _check_encryption_panic(agent_info.get("encryptionpanic"))


def _check_version(
    agent_version: str | None,
    site_version: str,
    expected_version: tuple[str, dict[str, str]],
    fail_state: State,
) -> CheckResult:
    if not agent_version:
        return

    rendered_mismatch = _render_agent_version_mismatch(
        agent_version, site_version, *expected_version
    )
    yield Result(
        state=fail_state if rendered_mismatch else State.OK,
        summary=f"Version: {agent_version}{rendered_mismatch}",
    )


def _render_agent_version_mismatch(
    agent_version: str,
    site_version: str,
    spec_type: str,
    spec: dict[str, str],
) -> str:
    if spec_type == "ignore":
        return ""

    if spec_type in ("specific", "site"):
        literal = spec.get("literal", site_version)
        return "" if literal == agent_version else f" (expected {literal})"

    # spec_type == "at_least"
    if _is_daily_build_version(agent_version) and (at_least := spec.get("daily_build")) is not None:
        if int(agent_version.split("-")[-1].replace(".", "")) < int(at_least.replace(".", "")):
            return f" (expected at least {at_least})"

    if (at_least := spec.get("release")) is None:
        return ""

    return (
        f" (expected at least {at_least})"
        if _is_daily_build_version(agent_version)
        or (parse_check_mk_version(agent_version) < parse_check_mk_version(at_least))
        else ""
    )


def _check_only_from(
    agent_only_from: None | str | Sequence[str],
    config_only_from: None | str | list[str],
    fail_state: State,
) -> CheckResult:
    if agent_only_from is None or config_only_from is None:
        return

    allowed_nets = set(_expand_curly_address_notation(agent_only_from))
    expected_nets = set(_expand_curly_address_notation(config_only_from))
    if allowed_nets == expected_nets:
        yield Result(
            state=State.OK,
            notice=f"Allowed IP ranges: {' '.join(allowed_nets)}",
        )
        return

    infotexts = []
    exceeding = allowed_nets - expected_nets
    if exceeding:
        infotexts.append("exceeding: %s" % " ".join(sorted(exceeding)))

    missing = expected_nets - allowed_nets
    if missing:
        infotexts.append("missing: %s" % " ".join(sorted(missing)))

    yield Result(
        state=fail_state,
        summary=f"Unexpected allowed IP ranges ({', '.join(infotexts)})",
    )


def _check_python_plugins(
    agent_failed_plugins: str | None,
    agent_fail_reason: str | None,
) -> CheckResult:
    if agent_failed_plugins:
        yield Result(
            state=State.WARN,
            summary=f"Failed to execute python plugins: {agent_failed_plugins}"
            + (f" ({agent_fail_reason})" if agent_fail_reason else ""),
        )


def _check_encryption_panic(
    panic: str | None,
) -> CheckResult:
    if panic:
        yield Result(
            state=State.CRIT,
            summary="Failed to apply symmetric encryption, aborting communication.",
        )


def _check_agent_update(
    update_fail_reason: str | None,
    on_update_fail_action: str | None,
) -> CheckResult:
    if update_fail_reason and on_update_fail_action:
        yield Result(state=State.WARN, summary=f"{update_fail_reason} {on_update_fail_action}")


def _check_transport(
    ssh_transport: bool,
    controller_info: ControllerSection | None,
    fail_state: State,
) -> CheckResult:
    if ssh_transport:
        yield Result(state=State.OK, summary="Transport via SSH")
        return

    if (
        not controller_info
        or not controller_info.allow_legacy_pull
        or not controller_info.agent_socket_operational
    ):
        return

    yield Result(
        state=fail_state,
        summary="TLS is not activated on monitored host (see details)",
        details=(
            "The hosts agent supports TLS, but it is not being used.\n"
            "We strongly recommend to enable TLS by registering the host to the site "
            "(using the `cmk-agent-ctl register` command on the monitored host).\n"
            "NOTE: A registered host will refuse all unencrypted connections. "
            "If the host is monitored by multiple sites, you must register to all of them. "
            "This can be problematic if you are monitoring the same host from a site running "
            "Checkmk version 2.0 or earlier.\n"
            "If you can not register the host, you can configure missing TLS to be OK in the "
            'setting "State in case of available but not enabled TLS" of the ruleset '
            '"Checkmk Agent installation auditing".'
        ),
    )


def _get_error_result(error: str, params: Mapping[str, Any]) -> CheckResult:
    # Sometimes we get duplicate output. Until we find out why, fix the error message:
    if "last_check" in error and "last_update" in error and "error" in error:
        error = error.split("error", 1)[1].strip()

    if error == "None" or not error:
        return

    default_state = State.WARN
    summary = first_line if (first_line := error.split("\n")[0].strip()) else "See details"
    details = None if summary == error else error  # drop details if same as the summary
    if (
        # Keep in sync with corresponding gui code
        "deployment is currently globally disabled"
    ) in error.lower():
        yield Result(
            state=State(params.get("error_deployment_globally_disabled", default_state)),
            summary=summary,
            details=details,
        )
        return

    if (
        # Keep in sync with corresponding gui code
        "agent updates are disabled for host"
    ) in error.lower():
        yield Result(
            state=State(params.get("error_deployment_disabled_for_hostname", default_state)),
            summary=summary,
            details=details,
        )
        return

    yield Result(
        state=default_state,
        summary=f"Update error: {summary}",
        details=details,
    )


def _check_cmk_agent_update_certificates(parsed: CMKAgentUpdateSection) -> CheckResult:
    """check the certificate part of the agent updater section

    Write to details if:
    * A certificate is corrupt
    * A certificate is not valid anymore
    * There is no trusted certificate

    Yield metrics about:
    * When each certificate is about to become invalid
    * When the last certificate is about to become invalid

    We don't issue WARN/CRIT here because the certificates are centrally managed in the bakery, so
    the warning about an expiring certificate should also be issued centrally.
    Otherwise, we would receive identical warnings from each affected host.

    We call the certificate "agent signature key" in the service output, since it's merely an
    implementation detail that we wrap the (public) key in a certificate.
    """

    if parsed.trusted_certs is None:
        return

    amount_trusted = 0  # How many trusted certificates are configured
    longest_valid = -1.0  # How long is the longest running certificate valid?
    for number, cert_info in parsed.trusted_certs.items():
        if cert_info.corrupt:
            yield Result(state=State.OK, notice=f"Agent signature key #{number} is corrupt")
            continue

        assert cert_info.not_after is not None  # It is only None if cert is corrupt

        # comparing naive to aware datetimes raises anyway, but the assertion is less obscure
        assert cert_info.not_after.tzinfo is not None, "cert_info.not_after must be tz aware"
        duration_valid = cert_info.not_after - datetime.now(UTC)

        if duration_valid.total_seconds() < 0:
            yield Result(
                state=State.OK,
                notice=f"Agent signature key #{number} ({cert_info.common_name!r}) is expired",
            )
        else:
            amount_trusted += 1
            longest_valid = max(longest_valid, duration_valid.total_seconds())
            yield from check_levels_v1(
                duration_valid.total_seconds(),
                render_func=render.timespan,
                label=f"Time until agent signature key #{number} ({cert_info.common_name!r}) will expire",
                notice_only=True,
            )

    if amount_trusted == 0:
        yield Result(state=State.OK, notice="Agent updater has no trusted agent signature keys")
    else:
        yield from check_levels_v1(
            longest_valid,
            render_func=render.timespan,
            label="Time until all agent signature keys are expired",
            notice_only=True,
        )


def _check_cmk_agent_update(
    params: Mapping[str, Any],
    section_check_mk: CheckmkSection | None,
    section_cmk_update_agent_status: CMKAgentUpdateSection | None,
) -> CheckResult:
    if (
        section := (
            section_cmk_update_agent_status
            or CMKAgentUpdateSection.parse_checkmk_section(section_check_mk)
        )
    ) is None:
        return

    if section.error is not None:
        yield from _get_error_result(section.error, params)

    if (last_check := section.last_check) is None:
        yield Result(state=State.WARN, summary="No successful connect to server yet")
    else:
        if (age := time.time() - last_check) >= 0:
            yield from check_levels_v1(
                age,
                levels_upper=(2 * 3600 * 24, None),  # type: ignore[arg-type]
                render_func=render.timespan,
                label="Time since last update check",
                notice_only=True,
            )
        else:
            yield Result(
                state=State.OK,
                summary=(
                    f"Last update check appears to be {render.timespan(-age)}"
                    " in the future (check your system time)"
                ),
            )
        yield Result(
            state=State.OK,
            notice=f"Last update check: {render.datetime(last_check)}",
        )

    if last_update := section.last_update:
        yield Result(
            state=State.OK,
            summary=f"Last update: {render.datetime(float(last_update))}",
        )

    if update_url := section.update_url:
        # Note: Transformation of URLs from this check (check_mk-check_mk_agent) to icons
        # is disabled explicitly in cmk.gui.view_utils:format_plugin_output
        yield Result(state=State.OK, notice=f"Update URL: {update_url}")

    if update_agent_host_name := section.host_name:
        yield Result(
            state=State.OK, notice=f"Hostname used by cmk-update-agent: {update_agent_host_name}"
        )
        if (checkmk_host_name := params["host_name"]) != update_agent_host_name:
            yield Result(
                state=State.CRIT,
                summary=f"Hostname defined in Checkmk ({checkmk_host_name}) and cmk-update-agent configuration ({update_agent_host_name}) do not match",
            )

    if aghash := section.aghash:
        yield Result(state=State.OK, notice=f"Agent configuration: {aghash}")

    if pending := section.pending_hash:
        yield Result(state=State.OK, notice=f"Pending installation: {pending}")

    yield from _check_cmk_agent_update_certificates(section)


def _check_plugins(
    params: Mapping[str, Any],
    section: PluginSection,
) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Agent plug-ins: {len(section.plugins)}",
    )
    yield Result(
        state=State.OK,
        summary=f"Local checks: {len(section.local_checks)}",
    )
    yield from _check_versions_and_duplicates(
        section.plugins,
        params.get("versions_plugins"),
        params.get("exclude_pattern_plugins"),
        "Agent plug-in",
    )
    yield from _check_versions_and_duplicates(
        section.local_checks,
        params.get("versions_lchecks"),
        params.get("exclude_pattern_lchecks"),
        "Local check",
    )


def _check_versions_and_duplicates(
    plugins: Iterable[Plugin],
    version_params: Mapping[str, Any] | None,
    exclude_pattern: str | None,
    type_: str,
) -> CheckResult:
    if exclude_pattern is None:
        plugins = list(plugins)
    else:
        comp = re.compile(exclude_pattern)
        plugins = [p for p in plugins if not comp.search(p.name)]

    if version_params:
        yield from _check_min_version(
            plugins,
            version_params["min_versions"],
            State(version_params["mon_state_unparsable"]),
            type_,
        )

    yield from _check_duplicates(
        plugins,
        type_,
    )


def _check_min_version(
    plugins: Iterable[Plugin],
    levels_str: tuple[str, str],
    mon_state_unparsable: State,
    type_: str,
) -> CheckResult:
    levels = (parse_check_mk_version(levels_str[0]), parse_check_mk_version(levels_str[1]))

    render_info = {p.version_int: p.version for p in plugins}
    render_info.update(zip(levels, levels_str))

    for plugin in plugins:
        if plugin.version == "unversioned":
            yield Result(
                state=State.OK,
                notice=f"{type_} {plugin.name!r}: no version specified",
            )
        elif plugin.version_int is None:
            yield Result(
                state=mon_state_unparsable,
                summary=f"{type_} {plugin.name!r}: unable to parse version {plugin.version!r}",
            )
        else:
            yield from check_levels_v1(
                plugin.version_int,
                levels_lower=levels,
                render_func=lambda v: render_info[int(v)],
                label=f"{type_} {plugin.name!r}",
                notice_only=True,
            )


def _check_duplicates(
    plugins: Iterable[Plugin],
    type_: str,
) -> CheckResult:
    plugins_by_name: dict[str, list[Plugin]] = collections.defaultdict(list)
    for p in plugins:
        plugins_by_name[p.name].append(p)
    for name, plugins_with_name in plugins_by_name.items():
        if (count := len(plugins_with_name)) > 1:
            yield Result(
                state=State.WARN,
                summary=f"{type_} {name}: found {count} times",
                details="Consult the HW/SW Inventory for a complete list of files",
            )


def _check_controller_cert_validity(section: ControllerSection, now: float) -> CheckResult:
    for connection in section.connections:
        yield from check_levels_v1(
            connection.local.cert_info.to.timestamp() - now,
            levels_lower=(30 * 24 * 3600, 15 * 24 * 3600),  # (30 days, 15 days)
            render_func=render.timespan,
            label=(
                (
                    f"Time until controller certificate for `{site_id}`, "
                    f"issued by `{connection.local.cert_info.issuer}`, expires"
                )
                if (site_id := connection.get_site_id())
                else (
                    "Time until controller certificate issued by "
                    f"`{connection.local.cert_info.issuer}` (imported connection) expires"
                )
            ),
            notice_only=True,
        )


def _format_cached_plugin(plugin: CachedPlugin) -> str:
    plugin_info = f"Timeout: {plugin.timeout}s, PID: {plugin.pid}"

    if plugin.plugin_type is None:
        return f"{plugin.plugin_name} ({plugin_info})"

    return f"{plugin.plugin_name} ({render_plugin_type(plugin.plugin_type)}, {plugin_info})"


def _plugin_strings(plugins: Sequence[CachedPlugin]) -> tuple[str, str]:
    return (
        ", ".join(_format_cached_plugin(plugin) for plugin in plugins),
        ", ".join(plugin.plugin_name for plugin in plugins),
    )


def _check_cached_plugins(section_checkmk_cached_plugins: CachedPluginsSection) -> CheckResult:
    if section_checkmk_cached_plugins.timeout is not None:
        timeout_plugins_long, timeout_plugins_short = _plugin_strings(
            section_checkmk_cached_plugins.timeout
        )
        yield Result(
            state=State.WARN,
            summary=f"Timed out plugin(s): {timeout_plugins_short}",
            details=f"Cached plugins(s) that reached timeout: {timeout_plugins_long} - "
            "Corresponding output is outdated and/or dropped.",
        )

    if section_checkmk_cached_plugins.killfailed is not None:
        killfailed_plugins_long, killfailed_plugins_short = _plugin_strings(
            section_checkmk_cached_plugins.killfailed
        )
        yield Result(
            state=State.WARN,
            summary=f"Termination failed: {killfailed_plugins_short}",
            details="Cached plugins(s) that failed to be terminated after timeout: "
            f"{killfailed_plugins_long} - "
            "Dysfunctional until successful termination.",
        )


def check_checkmk_agent(
    params: Mapping[str, Any],
    section_check_mk: CheckmkSection | None,
    section_checkmk_agent_plugins: PluginSection | None,
    section_cmk_agent_ctl_status: ControllerSection | None,
    section_cmk_update_agent_status: CMKAgentUpdateSection | None,
    section_checkmk_cached_plugins: CachedPluginsSection | None,
) -> CheckResult:
    if section_check_mk is not None:
        yield from _check_cmk_agent_installation(
            params, section_check_mk, section_cmk_agent_ctl_status
        )
    yield from _check_cmk_agent_update(params, section_check_mk, section_cmk_update_agent_status)

    if section_checkmk_agent_plugins is not None:
        yield from _check_plugins(params, section_checkmk_agent_plugins)

    if section_cmk_agent_ctl_status:
        yield from _check_controller_cert_validity(section_cmk_agent_ctl_status, time.time())

    if section_checkmk_cached_plugins:
        yield from _check_cached_plugins(section_checkmk_cached_plugins)


check_plugin_checkmk_agent = CheckPlugin(
    name="checkmk_agent",
    service_name="Check_MK Agent",
    sections=[
        "check_mk",
        "checkmk_agent_plugins",
        "cmk_agent_ctl_status",
        "cmk_update_agent_status",
        "checkmk_cached_plugins",
    ],
    discovery_function=discover_checkmk_agent,
    check_function=check_checkmk_agent,
    # TODO: rename the ruleset?
    check_ruleset_name="agent_update",
    check_default_parameters={
        "agent_version": ("ignore", {}),
        "agent_version_missmatch": 1,
        "restricted_address_mismatch": 1,
        "legacy_pull_mode": 1,
        # This next entry will be postprocessed by the backend.
        # The "only_from" configuration is not a check parameter but it is configured as an Agent Bakery rule,
        # and controls the *deployment* of the only_from setting.
        # We want to use that very setting to check whether it is deployed correctly.
        # Don't try this hack at home, we are trained professionals.
        "only_from": ("cmk_postprocessed", "only_from", None),
        # This next entry will be postprocessed by the backend.
        "host_name": ("cmk_postprocessed", "host_name", None),
    },
)
