#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

_Section = Mapping[str, object]


# Unlike the other options, port can be defined multiple times
def _parse_ports(string_table: StringTable) -> list[int]:
    # lower to stay compatible with older plug-in versions
    return [int(line[1]) for line in string_table if line[0].lower() == "port"]


def _identity(x: object) -> object:
    return x


def _map_permit_root_login(value: str) -> str:
    if value in ["prohibit-password", "without-password"]:
        return "key-based"
    return value


_RELEVANT_SINGULAR_OPTIONS_PARSER: Mapping[str, Callable[[str], object]] = {
    "protocol": lambda x: ",".join(sorted(x.split(","))),
    "permitrootlogin": _map_permit_root_login,
    "passwordauthentication": _identity,
    "permitemptypasswords": _identity,
    "challengeresponseauthentication": _identity,
    "kbdinteractiveauthentication": _identity,
    "x11forwarding": _identity,
    "usepam": _identity,
    "ciphers": lambda x: sorted(x.split(",")),
}


def parse_sshd_config(string_table: StringTable) -> _Section:
    ports = _parse_ports(string_table)
    return {
        **({"port": ports} if ports else {}),
        **{
            key: _RELEVANT_SINGULAR_OPTIONS_PARSER[key](" ".join(line[1:]))
            for line in string_table
            # lower to stay compatible with older plug-in versions
            if (key := line[0].lower()) in _RELEVANT_SINGULAR_OPTIONS_PARSER
        },
    }


agent_section_sshd_config = AgentSection(
    name="sshd_config",
    parse_function=parse_sshd_config,
)


def discover_sshd_config(section: _Section) -> DiscoveryResult:
    yield Service()


_OPTIONS_TO_HUMAN_READABLE = {
    "protocol": "Protocols",
    "port": "Ports",
    "permitrootlogin": "Permit root login",
    "passwordauthentication": "Allow password authentication",
    "permitemptypasswords": "Permit empty passwords",
    "kbdinteractiveauthentication": "Allow keyboard-interactive authentication",
    "challengeresponseauthentication": "Allow challenge-response authentication",
    "x11forwarding": "Permit X11 forwarding",
    "usepam": "Use pluggable authentication module",
    "ciphers": "Ciphers",
}

_MISSING_OPTIONS_TO_HUMAN_READABLE = {
    "kbdinteractiveauthentication": "Allow keyboard-interactive/challenge-response authentication",
    "challengeresponseauthentication": "Allow keyboard-interactive/challenge-response authentication",
}


def _value_to_human_readable(v: object) -> str:
    return ", ".join(map(str, v)) if isinstance(v, list) else str(v)


def _adjust_params(*, params: Mapping[str, object], section: _Section) -> Mapping[str, object]:
    if params.get("permitrootlogin") == "without-password":
        params = {
            **params,
            "permitrootlogin": "key-based",
        }

    previous_sshd_config_variable_names = {
        "kbdinteractiveauthentication": "challengeresponseauthentication"
    }

    return {
        (
            deprecated_name
            if (
                (deprecated_name := previous_sshd_config_variable_names.get(option))
                and deprecated_name in section
            )
            else option
        ): value
        for option, value in params.items()
    }


def check_sshd_config(params: Mapping[str, object], section: _Section) -> CheckResult:
    params = _adjust_params(params=params, section=section)

    for option, val in section.items():
        state = State.OK
        summary = f"{_OPTIONS_TO_HUMAN_READABLE[option]}: {_value_to_human_readable(val)}"

        if (expected := params.get(option)) and expected != val:
            state = State.CRIT
            summary += f" (expected {_value_to_human_readable(expected)})"

        yield Result(state=state, summary=summary)

    for option in sorted(set(params) - set(section)):
        yield Result(
            state=State.CRIT,
            summary=f"{_MISSING_OPTIONS_TO_HUMAN_READABLE.get(option, _OPTIONS_TO_HUMAN_READABLE[option])}: not present in SSH daemon configuration",
        )


check_plugin_sshd_config = CheckPlugin(
    name="sshd_config",
    service_name="SSH daemon configuration",
    discovery_function=discover_sshd_config,
    check_function=check_sshd_config,
    check_ruleset_name="sshd_config",
    check_default_parameters={},
)
