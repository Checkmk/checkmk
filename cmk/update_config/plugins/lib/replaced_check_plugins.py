#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, MutableMapping

from cmk.checkengine.plugins import CheckPluginName

# Please keep this functionality even if we currently don't have any replaced check plugins!
_REPLACED_CHECK_PLUGINS: dict[CheckPluginName, CheckPluginName] = {
    # 3.0: metric backend -> data backend / telemetry metrics
    CheckPluginName("custom_query_metric_backend"): CheckPluginName("telemetry_custom_service"),
    CheckPluginName("metric_backend_omd"): CheckPluginName("data_backend_telemetry_metrics_omd"),
    # 3.0: fix the misspelled Eaton UPS environment plug-in
    CheckPluginName("ups_eaton_enviroment"): CheckPluginName("ups_eaton_environment"),
}

ALL_REPLACED_CHECK_PLUGINS: Mapping[CheckPluginName, CheckPluginName] = {
    **_REPLACED_CHECK_PLUGINS,
    **{
        old_name.create_management_name(): new_name.create_management_name()
        for old_name, new_name in _REPLACED_CHECK_PLUGINS.items()
    },
}


def rename_matched_check_plugins(
    event_rules: Iterable[object],
    replaced_check_plugins: Mapping[CheckPluginName, CheckPluginName] = ALL_REPLACED_CHECK_PLUGINS,
) -> bool:
    """Rename the replaced check plug-ins notification or alert handler rules match on

    The rules would otherwise silently stop matching the services of the plug-ins.
    Returns whether any rule was changed.
    """
    renames = {str(old): str(new) for old, new in replaced_check_plugins.items()}
    changed = False
    for event_rule in event_rules:
        match event_rule:
            case {"match_checktype": list(plugin_names)} if isinstance(event_rule, MutableMapping):
                new_names = [renames.get(name, name) for name in plugin_names]
                if new_names != plugin_names:
                    event_rule["match_checktype"] = new_names
                    changed = True
            case _:
                pass
    return changed
