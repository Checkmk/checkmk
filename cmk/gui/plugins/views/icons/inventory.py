#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.config as config
import cmk.gui.inventory as inventory
from cmk.gui.i18n import _
from cmk.gui.plugins.views.icons import Icon, icon_and_action_registry
from cmk.gui.plugins.views import url_to_view


@icon_and_action_registry.register
class InventoryIcon(Icon):
    @classmethod
    def ident(cls):
        return "inventory"

    def host_columns(self):
        return ["name"]

    def render(self, what, row, tags, custom_vars):
        if (what == "host" or row.get("service_check_command","").startswith("check_mk_active-cmk_inv!")) \
            and inventory.has_inventory(row["host_name"]):

            if not config.user.may("view.inv_host"):
                return

            return 'inv', _("Show Hardware/Software Inventory of this host"), url_to_view(
                row, 'inv_host')
