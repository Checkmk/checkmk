#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection
from cmk.plugins.ups.lib import DETECT_UPS_GENERIC


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.850.1"},
            id="TrippLite UPS exact OID",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.850.1.1.1"},
            id="TrippLite UPS extended OID",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.850.100"},
            id="TrippLite UPS other model",
        ),
    ],
)
def test_detect_ups_generic_tripplite(oid_data: Mapping[str, str]) -> None:
    assert evaluate_snmp_detection(detect_spec=DETECT_UPS_GENERIC, oid_value_getter=oid_data.get)


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.232.165.3"},
            id="HP UPS",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.476.1.42"},
            id="Liebert UPS",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.534.1"},
            id="Eaton UPS",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.2.1.33.1"},
            id="Standard UPS-MIB device",
        ),
    ],
)
def test_detect_ups_generic_other_vendors(oid_data: Mapping[str, str]) -> None:
    assert evaluate_snmp_detection(detect_spec=DETECT_UPS_GENERIC, oid_value_getter=oid_data.get)


@pytest.mark.parametrize(
    "oid_data",
    [
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.1"},
            id="Cisco device should not match",
        ),
        pytest.param(
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.2636.1.1.1"},
            id="Juniper device should not match",
        ),
    ],
)
def test_detect_ups_generic_non_ups_devices(oid_data: Mapping[str, str]) -> None:
    assert not evaluate_snmp_detection(
        detect_spec=DETECT_UPS_GENERIC, oid_value_getter=oid_data.get
    )
