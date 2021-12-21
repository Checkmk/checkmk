#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import bulletlink, SidebarSnapin, snapin_registry


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
        bulletlink(_("Homepage"), "https://checkmk.com", target="_blank")
        bulletlink(_("Documentation"), "https://docs.checkmk.com/master", target="_blank")
        bulletlink(_("Download"), "https://checkmk.com/download", target="_blank")
        html.close_ul()
