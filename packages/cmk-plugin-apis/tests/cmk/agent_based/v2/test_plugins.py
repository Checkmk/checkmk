#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator
from typing import Never

import pytest

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    exists,
    InventoryPlugin,
    SimpleSNMPSection,
    SNMPSection,
    SNMPTree,
)

INVALID_NAMES = ["", *"\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|"]


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_agent_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = AgentSection(name=str_name, parse_function=lambda x: x)


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_agent_parsed_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = AgentSection(name="foo", parsed_section_name=str_name, parse_function=lambda x: x)


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_simple_snmp_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = SimpleSNMPSection(
            name=str_name,
            detect=exists("1"),
            fetch=SNMPTree(base="1", oids=[]),
            parse_function=lambda x: x,
        )


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_simple_snmp_parsed_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = SimpleSNMPSection(
            name="foo",
            parsed_section_name=str_name,
            detect=exists("1"),
            fetch=SNMPTree(base="1", oids=[]),
            parse_function=lambda x: x,
        )


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_snmp_parsed_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = SNMPSection(
            name="foo",
            parsed_section_name=str_name,
            detect=exists("1"),
            fetch=(),
            parse_function=lambda x: x,
        )


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_snmp_section_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = SNMPSection(name=str_name, detect=exists("1"), fetch=(), parse_function=lambda x: x)


def _noop(*_a: object) -> Generator[Never]:
    yield from ()


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_check_plugin_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = CheckPlugin(
            name=str_name, service_name="foo", discovery_function=_noop, check_function=_noop
        )


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_inventory_plugin_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = InventoryPlugin(name=str_name, inventory_function=_noop)
