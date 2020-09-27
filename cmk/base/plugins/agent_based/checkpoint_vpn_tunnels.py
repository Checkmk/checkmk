#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    register,
    SNMPTree,
)
from .utils import checkpoint

register.snmp_section(
    name="checkpoint_inv_tunnels",
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.2620.500.9002.1",
            oids=[
                "1",  # tunnelPeerIpAddr
                "7",  # tunnelSourceIpAddr
                "2",  # tunnelPeerObjName
                "6",  # tunnelInterface
                "8"  # tunnelLinkPriority
            ],
        ),
    ],
    detect=checkpoint.DETECT,
)
