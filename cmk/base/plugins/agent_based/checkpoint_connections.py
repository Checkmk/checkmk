#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.25.3.0 19190

from cmk.base.plugins.agent_based.v0 import register, SNMPTree  # type: ignore[import]
from cmk.base.plugins.agent_based.utils import checkpoint  # type: ignore[import]


def parse_checkpoint_connections(string_table):
    raw_value = string_table[0][0][0]
    return {"count": int(raw_value)}


register.snmp_section(
    name="checkpoint_connections",
    parse_function=parse_checkpoint_connections,
    detect=checkpoint.DETECT,
    trees=[SNMPTree(base=".1.3.6.1.4.1.2620.1.1.25", oids=[3])],
)
