#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.utils.sectionname import SectionName

from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins


@pytest.mark.parametrize(
    "oid_data, detected, not_detected",
    [
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": (
                    "Cisco IOS Software, C2960X Software (C2960X-UNIVERSALK9-M), Version 15.2(6)E3, RELEASE SOFTWARE (fc3)\r\n"
                    "Technical Support: http://www.cisco.com/techsupport\r\n"
                    "Copyright (c) 1986-2019 by Cisco Systems, Inc.\r\n"
                    "Compiled Mon 15-Jul-19 03:19 by prod_rel_team"
                ),
                ".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*": "something",
            },
            {"cisco_cpu_multiitem"},
            {"cisco_cpu", "cisco_nexus_cpu"},
            id="Detect multiitem check if supported by cisco device",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": (
                    "Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), "
                    "RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, "
                    "Inc. Compiled 8/13/2012 11:00:00"
                ),
                ".1.3.6.1.4.1.9.9.305.1.1.1.0": "0",
            },
            {"cisco_nexus_cpu"},
            set(),
            id="Cisco Nexus on zero CPU util",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": (
                    "Cisco NX-OS(tm) n1000v, Software (n1000v-dk9), Version 5.2(1)SV3(2.8), "
                    "RELEASE SOFTWARE Copyright (c) 2002-2011 by Cisco Systems, "
                    "Inc. Device Manager Version nms.sro not found,  Compiled 12/2/2016 10:00:00"
                ),
                ".1.3.6.1.4.1.9.9.305.1.1.1.0": "2",
            },
            {"cisco_nexus_cpu"},
            {"cisco_cpu"},
            id="Cisco Nexus on active CPU, make sure it is not discovered as cisco_cpu: SUP-3795",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": (
                    "Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), "
                    "RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, "
                    "Inc. Compiled 8/13/2012 11:00:00"
                ),
                ".1.3.6.1.4.1.9.9.305.1.1.1.0": None,
                ".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1": "9",
            },
            {"cisco_cpu"},
            {"cisco_nexus_cpu"},
            id="Cisco Nexus device, yet without the required OID",
        ),
    ],
)
def test_cisco_related_snmp_detection(
    agent_based_plugins: AgentBasedPlugins,
    oid_data: Mapping[str, str],
    detected: set[str],
    not_detected: set[str],
) -> None:
    for name in detected | not_detected:
        section = agent_based_plugins.snmp_sections[SectionName(name)]

        assert evaluate_snmp_detection(
            detect_spec=section.detect_spec,
            oid_value_getter=oid_data.get,
        ) == (name in detected), (
            f"make sure that {name} is{'' if name in detected else ' not'} detected"
        )
