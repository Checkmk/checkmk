#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

import cmk.snmplib.snmp_modes as snmp_modes

import cmk.base.check_api as check_api
import cmk.base.config as config
import cmk.base.snmp_scan as snmp_scan
from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,)

config.load_all_checks(check_api.get_check_api_context)

SNMP_SCAN_FUNCTIONS = config.snmp_scan_functions.copy()


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
    ])
def test_snmp_scan_functions(monkeypatch, name, oids_data, expected_result):
    def oid_function(oid, _default=None, _name=None):
        return oids_data.get(oid)

    monkeypatch.setattr(snmp_modes, "get_single_oid", lambda oid, *a, **kw: oids_data.get(oid))

    scan_function = SNMP_SCAN_FUNCTIONS[name]
    assert bool(scan_function(oid_function)) is expected_result

    converted_detect_spec = create_detect_spec(name, scan_function, [])
    actual_result = snmp_scan._evaluate_snmp_detection(
        converted_detect_spec,
        None,  # type: ignore # not used
        name,
        None,  # type: ignore # not used
        backend=None,  # type: ignore  # monkeypatched
    )
    assert actual_result is expected_result
