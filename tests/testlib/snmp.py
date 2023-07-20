#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Any, Final

from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import BackendSNMPTree, get_snmp_table, SNMPBackendEnum, SNMPHostConfig
from cmk.snmplib.detect import evaluate_snmp_detection

from cmk.fetchers.snmp_backend import StoredWalkSNMPBackend

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin

SNMP_HOST_CONFIG: Final = SNMPHostConfig(
    False,
    HostName("unittest"),
    HostAddress("127.0.0.1"),
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
)


def snmp_is_detected(section_name: SectionName, snmp_walk: Path) -> bool:
    section = agent_based_register.get_snmp_section_plugin(section_name)
    assert isinstance(section, SNMPSectionPlugin)

    backend = StoredWalkSNMPBackend(SNMP_HOST_CONFIG, logging.getLogger("test"), snmp_walk)

    def oid_value_getter(oid: str) -> str | None:
        value = backend.get(oid)
        if value is None:
            return None
        return backend.config.ensure_str(value)

    return evaluate_snmp_detection(
        detect_spec=section.detect_spec,
        oid_value_getter=oid_value_getter,
    )


def get_parsed_snmp_section(section_name: SectionName, snmp_walk: Path) -> Any | None:
    backend = StoredWalkSNMPBackend(SNMP_HOST_CONFIG, logging.getLogger("test"), snmp_walk)

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
