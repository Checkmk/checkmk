#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import SidebarSnapin, snapin_registry, bulletlink


@snapin_registry.register
class About(SidebarSnapin):
    @staticmethod
    def type_name():
        return "about"

    @classmethod
    def title(cls):
        return _("About Checkmk")

    @classmethod
    def description(cls):
        return _("Links to webpage, documentation and download of Checkmk")

    def show(self):
        html.open_ul()
        bulletlink(_("Homepage"), "https://checkmk.com/check_mk.html", target="_blank")
        bulletlink(_("Documentation"), "https://checkmk.com/cms.html", target="_blank")
        bulletlink(_("Download"), "https://checkmk.com/download.php", target="_blank")
        html.close_ul()
