#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main entry page for configuration of global variables, rules, groups,
timeperiods, users, etc."""

from cmk.gui.i18n import _

from cmk.gui.plugins.wato.utils.main_menu import (
    MainMenu,
    get_modules,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    changelog_button,
)


@mode_registry.register
class ModeMain(WatoMode):
    @classmethod
    def name(cls):
        return "main"

    @classmethod
    def permissions(cls):
        return []

    def title(self):
        return _("WATO - Check_MK's Web Administration Tool")

    def buttons(self):
        changelog_button()

    def page(self):
        MainMenu(get_modules()).show()
