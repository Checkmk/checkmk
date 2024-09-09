#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.checking import CheckPluginName

REPLACED_CHECK_PLUGINS: dict[CheckPluginName, CheckPluginName] = {
    CheckPluginName("arbor_peakflow_sp"): CheckPluginName("arbor_memory"),
    CheckPluginName("arbor_peakflow_tms"): CheckPluginName("arbor_memory"),
    CheckPluginName("arbor_peakflow_pravail"): CheckPluginName("arbor_memory"),
    CheckPluginName("f5_bigip_mem_tmm"): CheckPluginName("f5_bigip_mem"),
    CheckPluginName("mysql_slave"): CheckPluginName("mysql_replica_slave"),
}
