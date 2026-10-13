#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP Commons"""

from collections.abc import Mapping
from typing import Literal, TypedDict

from cmk.agent_based.v2 import all_of, contains, matches, not_matches

OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"
OID_F5_BIG_IP_bigipTrafficMgmt = ".1.3.6.1.4.1.3375.2"
OID_F5_BIG_IP_sysProductName = ".1.3.6.1.4.1.3375.2.1.4.1.0"
OID_F5_BIG_IP_sysProductVersion = ".1.3.6.1.4.1.3375.2.1.4.2.0"
# https://regex101.com/r/QRF2gl/2
VERSION_GE_V11_2_PATTERN = r"^(([2-9]\d|1[2-9])\.\d{1,}|11\.([2-9]|\d{2,}))(\.\d+)*$"
# https://regex101.com/r/QRF2gl/3
VERSION_GE_V11_PATTERN = r"^((1[1-9])|([2-9]\d))(\.\d+)*$"

F5_BIGIP = all_of(
    contains(OID_sysObjectID, OID_F5_BIG_IP_bigipTrafficMgmt),
    contains(OID_F5_BIG_IP_sysProductName, "big-ip"),
)

VERSION_PRE_V11_2 = not_matches(OID_F5_BIG_IP_sysProductVersion, VERSION_GE_V11_2_PATTERN)
VERSION_V11_2_PLUS = matches(OID_F5_BIG_IP_sysProductVersion, VERSION_GE_V11_2_PATTERN)

VERSION_PRE_V11 = not_matches(OID_F5_BIG_IP_sysProductVersion, VERSION_GE_V11_PATTERN)
VERSION_V11_PLUS = matches(OID_F5_BIG_IP_sysProductVersion, VERSION_GE_V11_PATTERN)

F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS = {
    "type": "active_standby",
}


class _F5BigipClusterStatusVSResultRequired(TypedDict, total=False):
    type: Literal["active_standby", "active_active"]


class F5BigipClusterStatusVSResult(_F5BigipClusterStatusVSResultRequired):
    # Keyed by the failover status names of cmk/plugins/f5_bigip/rulesets/cluster_status.py
    v11_2_states: Mapping[str, int]
