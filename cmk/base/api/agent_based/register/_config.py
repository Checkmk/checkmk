#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, Optional

from cmk.utils.type_defs import CheckPluginName
from cmk.utils.check_utils import is_management_name, MANAGEMENT_NAME_PREFIX

from cmk.base.api.agent_based.register.check_plugins import management_plugin_factory

from cmk.base.api.agent_based.type_defs import CheckPlugin

registered_check_plugins: Dict[CheckPluginName, CheckPlugin] = {}


def add_check_plugin(check_plugin: CheckPlugin) -> None:
    registered_check_plugins[check_plugin.name] = check_plugin


def is_registered_check_plugin(check_plugin_name: CheckPluginName):
    return check_plugin_name in registered_check_plugins


def get_check_plugin(plugin_name: CheckPluginName) -> Optional[CheckPlugin]:
    """Returns the registered check plugin

    Management plugins may be created on the fly.
    """
    plugin = registered_check_plugins.get(plugin_name)
    if plugin is not None or not is_management_name(plugin_name):
        return plugin

    # create management board plugin on the fly:
    non_mgmt_name = CheckPluginName(str(plugin_name)[len(MANAGEMENT_NAME_PREFIX):])
    non_mgmt_plugin = registered_check_plugins.get(non_mgmt_name)
    if non_mgmt_plugin is not None:
        return management_plugin_factory(non_mgmt_plugin)

    return None


def iter_all_check_plugins() -> Iterable[CheckPlugin]:
    return registered_check_plugins.values()  # pylint: disable=dict-values-not-iterating
