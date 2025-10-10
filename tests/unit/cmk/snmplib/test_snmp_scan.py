#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


import logging
from collections.abc import Iterator

import pytest

import cmk.fetchers._snmpscan as snmp_scan
from cmk.agent_based.v2 import SimpleSNMPSection, SNMPSection
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.plugins.collection.agent_based import aironet_clients, brocade_info
from cmk.snmplib import (
    SNMPBackend,
    SNMPBackendEnum,
    SNMPHostConfig,
    SNMPSectionName,
    SNMPVersion,
)
from cmk.snmplib._table import SNMPDecodedString
from cmk.utils.log import logger
from tests.unit.mocks_and_helpers import FixPluginLegacy


@pytest.mark.parametrize(
    "name, oids_data, expected_result",
    [
        (
            "quanta_fan",
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.8072.3.2.10"},
            False,
        ),
        (
            "quanta_fan",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.8072.3.2.10",
                ".1.3.6.1.4.1.7244.1.2.1.1.1.0": "exists",
            },
            True,
        ),
        # make sure casing is ignored
        (
            "hwg_humidity",
            {".1.3.6.1.2.1.1.1.0": "contains lower HWG"},
            True,
        ),
        (
            "hwg_ste2",
            {".1.3.6.1.2.1.1.1.0": "contains STE2"},
            True,
        ),
    ],
)
def test_evaluate_snmp_detection_legacy(
    fix_plugin_legacy: FixPluginLegacy,
    name: str,
    oids_data: dict[str, str | None],
    expected_result: bool,
) -> None:
    assert (detect_spec := fix_plugin_legacy.check_info[name].detect) is not None
    assert (
        snmp_scan._evaluate_snmp_detection(detect_spec=detect_spec, oid_value_getter=oids_data.get)
        is expected_result
    )


@pytest.mark.parametrize(
    "plugin, oids_data, expected_result",
    [
        (
            aironet_clients.snmp_section_aironet_clients,
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.5251"},
            False,
        ),
        (
            aironet_clients.snmp_section_aironet_clients,
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.525"},
            True,
        ),
        # for one example do all 6 permutations:
        (
            brocade_info.snmp_section_brocade_info,
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None",
            },
            True,
        ),
        (
            brocade_info.snmp_section_brocade_info,
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None,
            },
            False,
        ),
        (
            brocade_info.snmp_section_brocade_info,
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None",
            },
            True,
        ),
        (
            brocade_info.snmp_section_brocade_info,
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None,
            },
            False,
        ),
        (
            brocade_info.snmp_section_brocade_info,
            {".1.3.6.1.2.1.1.2.0": "Moo.Quack", ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"},
            False,
        ),
        (
            brocade_info.snmp_section_brocade_info,
            {".1.3.6.1.2.1.1.2.0": "Moo.Quack", ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None},
            False,
        ),
    ],
)
def test_evaluate_snmp_detection(
    plugin: SNMPSection | SimpleSNMPSection,
    oids_data: dict[str, str | None],
    expected_result: bool,
) -> None:
    assert (
        snmp_scan._evaluate_snmp_detection(
            detect_spec=plugin.detect, oid_value_getter=oids_data.get
        )
        is expected_result
    )


# C/P from `test_snmplib_snmp_table`.
SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress=HostAddress("1.2.3.4"),
    credentials="",
    port=42,
    bulkwalk_enabled=True,
    snmp_version=SNMPVersion.V2C,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


# Adapted from `test_snmplib_snmp_table`.
class SNMPTestBackend(SNMPBackend):
    def get(self, /, oid, *, context):
        # See also: `snmp_mode.get_single_oid()`
        return None

    def walk(self, /, oid, *, context, **kw):
        raise NotImplementedError("walk")


@pytest.fixture
def backend() -> Iterator[SNMPBackend]:
    yield SNMPTestBackend(SNMPConfig, logger)


@pytest.fixture
def single_oid_cache() -> Iterator[dict[str, SNMPDecodedString | None]]:
    # Cache OIDs to avoid actual SNMP I/O.
    yield {snmp_scan.OID_SYS_DESCR: "sys description", snmp_scan.OID_SYS_OBJ: "sys object"}


def test_snmp_scan_fake_description_object__success(backend: SNMPBackend) -> None:
    assert {
        snmp_scan.OID_SYS_DESCR: "",
        snmp_scan.OID_SYS_OBJ: "",
    } == snmp_scan._fake_description_object(logging.getLogger("test"))


def test_snmp_scan_find_plugins__success(
    backend: SNMPBackend,
    agent_based_plugins: AgentBasedPlugins,
    single_oid_cache: dict[str, SNMPDecodedString | None],
) -> None:
    sections = [
        (SNMPSectionName(s.name), s.detect_spec) for s in agent_based_plugins.snmp_sections.values()
    ]
    found = snmp_scan._find_sections(
        sections,
        {k: v for k, v in single_oid_cache.items() if v is not None},
        on_error=OnError.RAISE,
        backend=backend,
    )

    assert sections
    assert found
    assert len(sections) > len(found)


def test_gather_available_raw_section_names_defaults(
    backend: SNMPBackend,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    assert snmp_scan.gather_available_raw_section_names(
        [
            (SNMPSectionName(s.name), s.detect_spec)
            for s in agent_based_plugins.snmp_sections.values()
        ],
        scan_config=snmp_scan.SNMPScanConfig(
            on_error=OnError.RAISE,
            missing_sys_description=True,
        ),
        backend=backend,
    ) == {
        SNMPSectionName("hr_mem"),
        SNMPSectionName("snmp_info"),
        SNMPSectionName("snmp_uptime"),
    }
