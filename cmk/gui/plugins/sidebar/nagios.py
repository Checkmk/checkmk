#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class Nagios(SidebarSnapin):
    @staticmethod
    def type_name():
        return "nagios_legacy"

    @classmethod
    def title(cls):
        return _("Old Nagios GUI")

    @classmethod
    def description(cls):
        return _("The legacy Nagios GUI has been removed.")

    def show(self):
        html.write_text(_("The legacy Nagios GUI has been removed."))
