#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.f5os_rseries.agent_based.tenant import (
    check_f5os_rseries_tenant,
    discover_f5os_rseries_tenant,
    parse_f5os_rseries_tenant,
)

_TENANT_STRING_TABLE = [
    ["akof5ltmcmg11-1", "Running", "Started tenant instance"],
    ["akof5ltmcnp12-1", "Starting", ""],
    ["akof5ltmcpd12-1", "Stopped", "Tenant stopped"],
]


def test_parse_f5os_rseries_tenant() -> None:
    section = parse_f5os_rseries_tenant(_TENANT_STRING_TABLE)
    assert "akof5ltmcmg11-1" in section
    assert section["akof5ltmcmg11-1"].phase == "Running"
    assert section["akof5ltmcnp12-1"].phase == "Starting"
    assert section["akof5ltmcpd12-1"].phase == "Stopped"


def test_parse_f5os_rseries_tenant_empty() -> None:
    assert parse_f5os_rseries_tenant([]) == {}


def test_discover_f5os_rseries_tenant() -> None:
    section = parse_f5os_rseries_tenant(_TENANT_STRING_TABLE)
    services = sorted(discover_f5os_rseries_tenant(section), key=lambda s: s.item or "")
    assert len(services) == 3


@pytest.mark.parametrize(
    "item,expected_state",
    [
        ("akof5ltmcmg11-1", State.OK),  # Running
        ("akof5ltmcnp12-1", State.WARN),  # Starting
        ("akof5ltmcpd12-1", State.CRIT),  # Stopped
    ],
)
def test_check_f5os_rseries_tenant_states(item: str, expected_state: State) -> None:
    section = parse_f5os_rseries_tenant(_TENANT_STRING_TABLE)
    results = list(check_f5os_rseries_tenant(item, section))
    states = [r.state for r in results if isinstance(r, Result)]
    assert expected_state in states


def test_check_f5os_rseries_tenant_missing_item() -> None:
    section = parse_f5os_rseries_tenant(_TENANT_STRING_TABLE)
    results = list(check_f5os_rseries_tenant("nonexistent", section))
    assert results == []
