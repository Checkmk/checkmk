#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from typing import Any

from cmk.utils.type_defs import SectionName

from cmk.snmplib.snmp_table import get_snmp_table
from cmk.snmplib.type_defs import BackendSNMPTree, SNMPBackendEnum, SNMPHostConfig
from cmk.snmplib.utils import evaluate_snmp_detection

from cmk.fetchers.snmp_backend import StoredWalkSNMPBackend

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin


class _StringSNMPBackend(StoredWalkSNMPBackend):
    counter = 0  # bust that cache!

    def __init__(self, data_string):
        self.lines = [l for l in data_string.split("\n") if l]
        _StringSNMPBackend.counter += 1
        super().__init__(
            SNMPHostConfig(
                False,
                f"unittest-{_StringSNMPBackend.counter}",
                "127.0.0.1",
                "",
                0,
                False,
                False,
                0,
                {},
                {},
                [],
                None,
                SNMPBackendEnum.STORED_WALK,
            ),
            logging.getLogger("tbd"),
        )

    def read_walk_data(self) -> Sequence[str]:
        return self.lines


def snmp_is_detected(section_name: SectionName, snmp_walk: str) -> bool:
    section = agent_based_register.get_snmp_section_plugin(section_name)
    assert isinstance(section, SNMPSectionPlugin)

    backend = _StringSNMPBackend(snmp_walk)

    def oid_value_getter(oid: str) -> str | None:
        value = backend.get(oid)
        if value is None:
            return None
        return backend.config.ensure_str(value)

    return evaluate_snmp_detection(
        detect_spec=section.detect_spec,
        oid_value_getter=oid_value_getter,
    )


def get_parsed_snmp_section(section_name: SectionName, snmp_walk: str) -> Any | None:
    backend = _StringSNMPBackend(snmp_walk)

    section = agent_based_register.get_snmp_section_plugin(section_name)
    assert isinstance(section, SNMPSectionPlugin)

    table = []
    for tree in section.trees:
        table.append(
            get_snmp_table(
                section_name=section.name,
                tree=BackendSNMPTree.from_frontend(base=tree.base, oids=tree.oids),
                walk_cache={},
                backend=backend,
            )
        )

    result = section.parse_function(table)  # type: ignore[arg-type]
    return result
