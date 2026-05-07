#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.plugins.cisco.agent_based import aironet_clients


@pytest.mark.parametrize(
    "oids_data, expected_result",
    [
        (
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.5251"},
            False,
        ),
        (
            {".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.525"},
            True,
        ),
    ],
)
def test_detect_aironet_clients(
    oids_data: dict[str, str | None],
    expected_result: bool,
) -> None:
    assert (
        evaluate_snmp_detection(
            detect_spec=aironet_clients.snmp_section_aironet_clients.detect,
            oid_value_getter=oids_data.get,
        )
        is expected_result
    )
