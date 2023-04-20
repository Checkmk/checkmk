#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access, redefined-outer-name

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from tests.testlib.base import Scenario

from tests.unit.conftest import FixPluginLegacy

from cmk.utils.exceptions import OnError
from cmk.utils.log import logger
from cmk.utils.paths import snmp_scan_cache_dir
from cmk.utils.type_defs import HostName, SectionName

import cmk.snmplib.snmp_cache as snmp_cache
import cmk.snmplib.snmp_scan as snmp_scan
from cmk.snmplib.type_defs import OID, SNMPBackend, SNMPBackendEnum, SNMPHostConfig
from cmk.snmplib.utils import evaluate_snmp_detection

import cmk.base.api.agent_based.register as agent_based_register


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
        (
            "aironet_clients",
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.5251"},
            False,
        ),
        (
            "aironet_clients",
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.525"},
            True,
        ),
        # for one example do all 6 permutations:
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None",
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None,
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None",
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None,
            },
            False,
        ),
        (
            "brocade_info",
            {".1.3.6.1.2.1.1.2.0": "Moo.Quack", ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"},
            False,
        ),
        (
            "brocade_info",
            {".1.3.6.1.2.1.1.2.0": "Moo.Quack", ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None},
            False,
        ),
    ],
)
def test_evaluate_snmp_detection(
    fix_plugin_legacy: FixPluginLegacy,
    name: str,
    oids_data: dict[str, str | None],
    expected_result: bool,
) -> None:
    assert (
        evaluate_snmp_detection(
            detect_spec=fix_plugin_legacy.check_info[name]["detect"],
            oid_value_getter=oids_data.get,
        )
        is expected_result
    )


# C/P from `test_snmplib_snmp_table`.
SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress="1.2.3.4",
    credentials="",
    port=42,
    is_bulkwalk_host=False,
    is_snmpv2or3_without_bulkwalk_host=False,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


# Adapted from `test_snmplib_snmp_table`.
class SNMPTestBackend(SNMPBackend):
    def get(self, oid, context_name=None):
        # See also: `snmp_mode.get_single_oid()`
        return None

    def walk(self, oid, section_name=None, table_base_oid=None, context_name=None):
        raise NotImplementedError("walk")


@pytest.fixture
def backend() -> Iterator[SNMPBackend]:
    try:
        yield SNMPTestBackend(SNMPConfig, logger)
    finally:
        cachefile = Path(snmp_scan_cache_dir, f"{SNMPConfig.hostname}.{SNMPConfig.ipaddress}")
        try:
            cachefile.unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def scenario(backend, monkeypatch):
    # Set the `ruleset_matcher` on the config.
    ts = Scenario()
    ts.add_host(backend.hostname)
    ts.apply(monkeypatch)


@pytest.fixture
def cache_oids(backend):
    # Cache OIDs to avoid actual SNMP I/O.
    snmp_cache.initialize_single_oid_cache(backend.config.hostname, backend.config.ipaddress)
    snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR] = "sys description"
    snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ] = "sys object"
    yield
    snmp_cache._clear_other_hosts_oid_cache(backend.hostname)


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
@pytest.mark.parametrize("oid", [snmp_scan.OID_SYS_DESCR, snmp_scan.OID_SYS_OBJ])
def test_snmp_scan_prefetch_description_object__oid_missing(oid: OID, backend: SNMPBackend) -> None:
    snmp_cache.single_oid_cache()[oid] = None

    with pytest.raises(snmp_scan.MKSNMPError, match=r"Cannot fetch [\w ]+ OID %s" % oid):
        snmp_scan._prefetch_description_object(backend=backend)


@pytest.mark.usefixtures("scenario")
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


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_fake_description_object__success(backend: SNMPBackend) -> None:
    snmp_scan._fake_description_object()

    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR] == ""
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ] == ""


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_find_plugins__success(backend: SNMPBackend) -> None:
    sections = [(s.name, s.detect_spec) for s in agent_based_register.iter_all_snmp_sections()]
    found = snmp_scan._find_sections(
        sections,
        on_error=OnError.RAISE,
        backend=backend,
    )

    assert sections
    assert found
    assert len(sections) > len(found)


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_gather_available_raw_section_names_defaults(
    backend: SNMPBackend, mocker: MockerFixture
) -> None:
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_DESCR]
    assert snmp_cache.single_oid_cache()[snmp_scan.OID_SYS_OBJ]

    assert snmp_scan.gather_available_raw_section_names(
        [(s.name, s.detect_spec) for s in agent_based_register.iter_all_snmp_sections()],
        on_error=OnError.RAISE,
        missing_sys_description=False,
        backend=backend,
    ) == {
        SectionName("hr_mem"),
        SectionName("snmp_info"),
        SectionName("snmp_uptime"),
    }
