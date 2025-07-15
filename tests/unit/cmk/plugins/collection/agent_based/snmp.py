#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Any, Final

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.snmplib import (
    BackendSNMPTree,
    ensure_str,
    get_snmp_table,
    SNMPBackendEnum,
    SNMPHostConfig,
    SNMPVersion,
)

from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection
from cmk.fetchers.snmp_backend import StoredWalkSNMPBackend

from cmk.checkengine.plugin_backend.section_plugins import create_snmp_section_plugin

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPSection
from cmk.discover_plugins import PluginLocation

SNMP_HOST_CONFIG: Final = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("unittest"),
    ipaddress=HostAddress("127.0.0.1"),
    credentials="",
    port=0,
    bulkwalk_enabled=True,
    snmp_version=SNMPVersion.V2C,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding=None,
    snmp_backend=SNMPBackendEnum.STORED_WALK,
)


def snmp_is_detected(section: SNMPSection | SimpleSNMPSection, snmp_walk: Path) -> bool:
    section_plugin = create_snmp_section_plugin(
        section, PluginLocation("not", "relevant"), validate=True
    )

    backend = StoredWalkSNMPBackend(SNMP_HOST_CONFIG, logging.getLogger("test"), snmp_walk)

    def oid_value_getter(oid: str) -> str | None:
        value = backend.get(oid, context="")
        if value is None:
            return None
        return ensure_str(value, encoding=backend.config.character_encoding)

    return evaluate_snmp_detection(
        detect_spec=section_plugin.detect_spec,
        oid_value_getter=oid_value_getter,
    )


def get_parsed_snmp_section(
    section: SNMPSection | SimpleSNMPSection, snmp_walk: Path
) -> Any | None:
    logger = logging.getLogger("test")
    backend = StoredWalkSNMPBackend(SNMP_HOST_CONFIG, logger, snmp_walk)

    section_plugin = create_snmp_section_plugin(
        section, PluginLocation("not", "relevant"), validate=True
    )

    table = []
    for tree in section_plugin.trees:
        table.append(
            get_snmp_table(
                section_name=section_plugin.name,
                tree=BackendSNMPTree.from_frontend(base=tree.base, oids=tree.oids),
                walk_cache={},
                backend=backend,
                log=logger.debug,
            )
        )

    result = section_plugin.parse_function(table)  # type: ignore[arg-type]
    return result
