#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import SectionName

from cmk.snmplib.utils import evaluate_snmp_detection
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin


@pytest.mark.parametrize('oid_data, detected, not_detected', [
    pytest.param(
        {
            ".1.3.6.1.2.1.1.1.0":
                ("Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), "
                 "RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, "
                 "Inc. Compiled 8/13/2012 11:00:00"),
            ".1.3.6.1.4.1.9.9.305.1.1.1.0": "0"
        },
        {"cisco_nexus_cpu"},
        set(),
        id="Cisco Nexus on zero CPU util",
    ),
    pytest.param(
        {
            ".1.3.6.1.2.1.1.1.0":
                ("Cisco NX-OS(tm) n1000v, Software (n1000v-dk9), Version 5.2(1)SV3(2.8), "
                 "RELEASE SOFTWARE Copyright (c) 2002-2011 by Cisco Systems, "
                 "Inc. Device Manager Version nms.sro not found,  Compiled 12/2/2016 10:00:00"),
            ".1.3.6.1.4.1.9.9.305.1.1.1.0": "2",
        },
        {"cisco_nexus_cpu"},
        {"cisco_cpu"},
        id="Cisco Nexus on active CPU, make sure it is not discovered as cisco_cpu: SUP-3795",
    ),
    pytest.param(
        {
            ".1.3.6.1.2.1.1.1.0":
                ("Cisco NX-OS(tm) m9100, Software (m9100-s2ek9-mz), Version 5.2(6a), "
                 "RELEASE SOFTWARE Copyright (c) 2002-2012 by Cisco Systems, "
                 "Inc. Compiled 8/13/2012 11:00:00"),
            ".1.3.6.1.4.1.9.9.305.1.1.1.0": None,
            ".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1": "9",
        },
        {"cisco_cpu"},
        {"cisco_nexus_cpu"},
        id="Cisco Nexus device, yet without the required OID",
    ),
])
@pytest.mark.usefixtures('config_load_all_checks')
def test_cisco_related_snmp_detection(oid_data, detected, not_detected):

    for name in detected | not_detected:
        section = agent_based_register.get_section_plugin(SectionName(name))
        assert isinstance(section, SNMPSectionPlugin)

        assert evaluate_snmp_detection(
            detect_spec=section.detect_spec,
            oid_value_getter=oid_data.get,
        ) == (name in detected)
