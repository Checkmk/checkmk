#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info

check_info["apc_rackpdu_power"] = {
    # section already migrated
    "discovery_function": discover(),
    "check_function": check_elphase,
    "service_name": "PDU %s",
    "check_ruleset_name": "el_inphase",
}
