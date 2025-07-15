#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.unit.mocks_and_helpers import FixPluginLegacy

from cmk.ccc.exceptions import MKSNMPError, OnError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.log import logger
from cmk.utils.paths import snmp_scan_cache_dir
from cmk.utils.sectionname import SectionName

from cmk.snmplib import OID, SNMPBackend, SNMPBackendEnum, SNMPHostConfig, SNMPVersion

import cmk.fetchers._snmpcache as snmp_cache
import cmk.fetchers._snmpscan as snmp_scan

from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPSection
from cmk.plugins.collection.agent_based import aironet_clients, brocade_info


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
    try:
        yield SNMPTestBackend(SNMPConfig, logger)
    finally:
        cachefile = snmp_scan_cache_dir / f"{SNMPConfig.hostname}.{SNMPConfig.ipaddress}"
        try:
            cachefile.unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def cache_oids(backend, tmp_path):
    # Cache OIDs to avoid actual SNMP I/O.
    snmp_cache.initialize_single_oid_cache(
        backend.config.hostname, backend.config.ipaddress, cache_dir=tmp_path
    )
    snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR] = "sys description"
    snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ] = "sys object"
    yield
    snmp_cache._clear_other_hosts_oid_cache(backend.hostname)


@pytest.mark.usefixtures("cache_oids")
@pytest.mark.parametrize("oid", [snmp_scan.OID_SYS_DESCR, snmp_scan.OID_SYS_OBJ])
def test_snmp_scan_prefetch_description_object__oid_missing(oid: OID, backend: SNMPBackend) -> None:
    snmp_cache.single_oid_cache()[oid] = None

    with pytest.raises(MKSNMPError, match=r"Cannot fetch [\w ]+ OID %s" % oid):
        snmp_scan._prefetch_description_object(backend=backend)


@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_prefetch_description_object__success(backend: SNMPBackend) -> None:
    sys_desc = snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR]
    sys_obj = snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ]
    assert sys_desc
    assert sys_obj

    snmp_scan._prefetch_description_object(backend=backend)

    # Success is no-op
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR] == sys_desc
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ] == sys_obj


@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_fake_description_object__success(backend: SNMPBackend) -> None:
    snmp_scan._fake_description_object(logging.getLogger("test"))

    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR] == ""
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ] == ""


@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_find_plugins__success(
    backend: SNMPBackend,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    sections = [(s.name, s.detect_spec) for s in agent_based_plugins.snmp_sections.values()]
    found = snmp_scan._find_sections(
        sections,
        on_error=OnError.RAISE,
        backend=backend,
    )

    assert sections
    assert found
    assert len(sections) > len(found)


@pytest.mark.usefixtures("cache_oids")
def test_gather_available_raw_section_names_defaults(
    backend: SNMPBackend,
    tmp_path: Path,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR]
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ]

    assert snmp_scan.gather_available_raw_section_names(
        [(s.name, s.detect_spec) for s in agent_based_plugins.snmp_sections.values()],
        scan_config=snmp_scan.SNMPScanConfig(
            on_error=OnError.RAISE,
            missing_sys_description=False,
            oid_cache_dir=tmp_path,
        ),
        backend=backend,
    ) == {
        SectionName("hr_mem"),
        SectionName("snmp_info"),
        SectionName("snmp_uptime"),
    }
