#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.utils.brocade import (  # pylint: disable=unused-import
    brocade_fcport_getitem,
    brocade_fcport_inventory_this_port,
)

# This is the variable for the actual rule
brocade_fcport_inventory: list = []
