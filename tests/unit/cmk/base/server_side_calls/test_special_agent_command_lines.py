#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Never

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ruleset_matcher.matcher import RuleSpec
from tests.testlib.unit.base_configuration_scenario import Scenario

_HOST = HostName("jolokia-host")


@dataclass(frozen=True)
class _SecretsConfig:
    path: Path
    secrets: Mapping[str, Never]


def _command_lines(
    monkeypatch: pytest.MonkeyPatch, address: HostAddress
) -> Sequence[tuple[str, object]]:
    rule: RuleSpec[Mapping[str, object]] = {
        "condition": {"host_name": [_HOST]},
        "id": "01",
        "value": {},
    }
    ts = Scenario()
    ts.add_host(_HOST)
    ts.set_ruleset_bundle("special_agents", {"jolokia": [rule]})
    config_cache = ts.apply(monkeypatch).config_cache
    return list(
        config_cache.special_agent_command_lines(
            _HOST,
            socket.AddressFamily.AF_INET,
            address,
            secrets_config=_SecretsConfig(path=Path("/pw/store"), secrets={}),
            ip_address_of=lambda *a: address,  # noqa: ARG005
            executable_finder=lambda name, module: "/omd/bin/agent_jolokia",  # noqa: ARG005
            for_relay=False,
        )
    )


@pytest.mark.parametrize("unspecified", (HostAddress("0.0.0.0"), HostAddress("::")))
def test_unspecified_address_is_not_passed_to_a_special_agent(
    unspecified: HostAddress, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plug-in must not be handed an address that reaches the local system.

    `IPConfig.address` already raises for a missing address; the unspecified
    one used to slip past it because it looks like an ordinary address.
    """
    with pytest.raises(RuntimeError, match="Host address lookup failed"):
        _command_lines(monkeypatch, unspecified)


def test_a_usable_address_still_reaches_the_special_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (_agent_name, command_line), *_ = _command_lines(monkeypatch, HostAddress("192.0.2.1"))
    assert "192.0.2.1" in command_line.cmdline  # type: ignore[attr-defined]
