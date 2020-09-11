#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access, redefined-outer-name

from pathlib import Path

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.log import logger
from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_cache as snmp_cache
import cmk.snmplib.snmp_scan as snmp_scan
from cmk.snmplib.snmp_scan import SNMPScanSection
from cmk.snmplib.type_defs import ABCSNMPBackend, SNMPHostConfig
from cmk.snmplib.utils import evaluate_snmp_detection

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,)


def validate_snmp_detections(snmp_scan_functions, name, oids_data, expected_result):
    def oid_function(oid, _default=None, _name=None):
        return oids_data.get(oid)

    scan_function = snmp_scan_functions[name]
    assert bool(scan_function(oid_function)) is expected_result

    converted_detect_spec = create_detect_spec(name, scan_function, [])
    actual_result = evaluate_snmp_detection(
        detect_spec=converted_detect_spec,
        oid_value_getter=oids_data.get,
    )
    assert actual_result is expected_result


@pytest.mark.parametrize(
    "name, oids_data, expected_result",
    [
        (
            "quanta_fan",
            {
                '.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.8072.3.2.10'
            },
            False,
        ),
        (
            "quanta_fan",
            {
                '.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.8072.3.2.10',
                '.1.3.6.1.4.1.7244.1.2.1.1.1.0': "exists"
            },
            True,
        ),
        # make sure casing is ignored
        (
            "hwg_temp",
            {
                ".1.3.6.1.2.1.1.1.0": "contains lower HWG"
            },
            True,
        ),
        # make sure casing is ignored
        (
            "hwg_humidity",
            {
                ".1.3.6.1.2.1.1.1.0": "contains lower HWG"
            },
            True,
        ),
        (
            "hwg_ste2",
            {
                ".1.3.6.1.2.1.1.1.0": "contains STE2"
            },
            True,
        ),
        (
            "aironet_clients",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.5251"
            },
            False,
        ),
        (
            "aironet_clients",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.525"
            },
            True,
        ),
        # for one example do all 6 permutations:
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": "Moo.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": "Moo.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
        pytest.param(
            "cisco_nexus_cpu",
            {
                ".1.3.6.1.2.1.1.1.0": "Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, Inc. Compiled 8/13/2012 11:00:00",
                ".1.3.6.1.4.1.9.9.305.1.1.1.0": "0"
            },
            True,
            id="Cisco Nexus on zero CPU util",
        ),
    ])
def test_evaluate_snmp_detection(config_snmp_scan_functions, name, oids_data, expected_result):
    validate_snmp_detections(config_snmp_scan_functions, name, oids_data, expected_result)


@pytest.mark.parametrize("target, collisions, oids_data", [
    pytest.
    param("cisco_nexus_cpu", ["cisco_cpu"], {
        ".1.3.6.1.2.1.1.1.0": "Cisco NX-OS(tm) n1000v, Software (n1000v-dk9), Version 5.2(1)SV3(2.8), RELEASE SOFTWARE Copyright (c) 2002-2011 by Cisco Systems, Inc. Device Manager Version nms.sro not found,  Compiled 12/2/2016 10:00:00",
        ".1.3.6.1.4.1.9.9.305.1.1.1.0": "2",
    },
          id="Cisco Nexus on active CPU, make sure it is not discovered as cisco_cpu: SUP-3795"),
    pytest.param("cisco_cpu", ["cisco_nexus_cpu"], {
        ".1.3.6.1.2.1.1.1.0": "Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, Inc. Compiled 8/13/2012 11:00:00",
        ".1.3.6.1.4.1.9.9.305.1.1.1.0": None,
        ".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1": "9",
    },
                 id="Cisco Nexus device, yet without the required OID"),
])
def test_evaluate_snmp_detection_conflicts(config_snmp_scan_functions, target, collisions,
                                           oids_data):
    validate_snmp_detections(config_snmp_scan_functions, target, oids_data, True)
    for avoid in collisions:
        validate_snmp_detections(config_snmp_scan_functions, avoid, oids_data, False)


# C/P from `test_snmplib_snmp_table`.
SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname="testhost",
    ipaddress="1.2.3.4",
    credentials="",
    port=42,
    is_bulkwalk_host=False,
    is_snmpv2or3_without_bulkwalk_host=False,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits=[],
    snmpv3_contexts=[],
    character_encoding="ascii",
    is_usewalk_host=False,
    is_inline_snmp_host=False,
    record_stats=False,
)


# Adapted from `test_snmplib_snmp_table`.
class SNMPTestBackend(ABCSNMPBackend):
    def get(self, oid, context_name=None):
        raise NotImplementedError("get")

    def walk(self, oid, check_plugin_name=None, table_base_oid=None, context_name=None):
        raise NotImplementedError("walk")


@pytest.fixture
def backend():
    try:
        yield SNMPTestBackend(SNMPConfig, logger)
    finally:
        cachefile = Path("tmp/check_mk/snmp_scan_cache/%s.%s" %
                         (SNMPConfig.hostname, SNMPConfig.ipaddress))
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
    snmp_cache.initialize_single_oid_cache(backend.config)
    snmp_cache.set_single_oid_cache(snmp_scan.OID_SYS_DESCR, "sys description")
    snmp_cache.set_single_oid_cache(snmp_scan.OID_SYS_OBJ, "sys object")
    yield
    snmp_cache._clear_other_hosts_oid_cache(backend.hostname)


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
@pytest.mark.parametrize("oid", [snmp_scan.OID_SYS_DESCR, snmp_scan.OID_SYS_OBJ])
def test_snmp_scan_cache_description__oid_missing(oid, backend):
    snmp_cache.set_single_oid_cache(oid, None)

    with pytest.raises(snmp_scan.MKSNMPError, match=r"Cannot fetch [\w ]+ OID %s" % oid):
        snmp_scan._snmp_scan_cache_description(
            False,
            backend=backend,
        )


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_cache_description__success_non_binary(backend):
    sys_desc = snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_DESCR)
    sys_obj = snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_OBJ)
    assert sys_desc
    assert sys_obj

    snmp_scan._snmp_scan_cache_description(
        binary_host=False,
        backend=backend,
    )

    # Success is no-op
    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_DESCR) == sys_desc
    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_OBJ) == sys_obj


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_cache_description__success_binary(backend):
    snmp_scan._snmp_scan_cache_description(
        binary_host=True,
        backend=backend,
    )

    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_DESCR) == ""
    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_OBJ) == ""


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_snmp_scan_find_plugins__success(backend):
    sections = [
        SNMPScanSection(_.name, _.detect_spec)
        for _ in agent_based_register.iter_all_snmp_sections()
    ]
    found = snmp_scan._snmp_scan_find_sections(
        sections,
        on_error="raise",
        backend=backend,
    )

    assert sections
    assert found
    assert len(sections) > len(found)


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("cache_oids")
def test_gather_available_raw_section_names_defaults(backend, mocker):
    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_DESCR)
    assert snmp_cache.get_oid_from_single_oid_cache(snmp_scan.OID_SYS_OBJ)

    assert snmp_scan.gather_available_raw_section_names(
        [
            SNMPScanSection(_.name, _.detect_spec)
            for _ in agent_based_register.iter_all_snmp_sections()
        ],
        on_error="raise",
        binary_host=False,
        backend=backend,
    ) == {
        SectionName("hr_mem"),
        SectionName("mgmt_snmp_info"),
        SectionName("snmp_info"),
        SectionName("snmp_os"),
        SectionName("snmp_uptime"),
    }
