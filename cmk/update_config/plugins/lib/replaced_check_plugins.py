#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.checkengine.plugins import CheckPluginName

# Please keep this functionality even if we currently don't have any replaced check plugins!
_REPLACED_CHECK_PLUGINS: dict[CheckPluginName, CheckPluginName] = {
    CheckPluginName("tplink_mem"): CheckPluginName("memory_utilization")
}

ALL_REPLACED_CHECK_PLUGINS: Mapping[CheckPluginName, CheckPluginName] = {
    **_REPLACED_CHECK_PLUGINS,
    **{
        old_name.create_management_name(): new_name.create_management_name()
        for old_name, new_name in _REPLACED_CHECK_PLUGINS.items()
    },
}
