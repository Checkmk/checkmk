#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.utils.sectionname import SectionName

# pylint: disable=cmk-module-layer-violation
from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection

from cmk.checkengine.plugins import AgentBasedPlugins


@pytest.mark.parametrize(
    "oid_data, detected",
    [
        pytest.param(
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.12383.0.0.0",
            },
            {"safenet_hsm", "safenet_ntls"},
            id="SafeNet Luna HSM 6.x device",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.8072.3.1.1",
            },
            {"safenet_hsm", "safenet_ntls"},
            id="Thales SafeNet Luna S700 Series device",
        ),
    ],
)
def test_safenet_hsm_snmp_detection(
    agent_based_plugins: AgentBasedPlugins, oid_data: Mapping[str, str], detected: set[str]
) -> None:
    for name in detected:
        section = agent_based_plugins.snmp_sections[SectionName(name)]

        assert (
            evaluate_snmp_detection(
                detect_spec=section.detect_spec,
                oid_value_getter=oid_data.get,
            )
            is True
        )
