#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Register the builtin global setting configuration variable groups"""

from cmk.gui.i18n import _
from cmk.gui.plugins.watolib.utils import config_variable_group_registry, ConfigVariableGroup


@config_variable_group_registry.register
class ConfigVariableGroupNotifications(ConfigVariableGroup):
    def title(self):
        return _("Notifications")

    def sort_index(self):
        return 15


@config_variable_group_registry.register
class ConfigVariableGroupUserInterface(ConfigVariableGroup):
    def title(self):
        return _("User interface")

    def sort_index(self):
        return 20


@config_variable_group_registry.register
class ConfigVariableGroupWATO(ConfigVariableGroup):
    def title(self):
        return _("Setup")

    def sort_index(self):
        return 25


@config_variable_group_registry.register
class ConfigVariableGroupSiteManagement(ConfigVariableGroup):
    def title(self):
        return _("Site management")

    def sort_index(self):
        return 30
