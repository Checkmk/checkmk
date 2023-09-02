#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.type_defs import Icon
from cmk.gui.wato import MainModuleTopicGeneral
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleTopic


class MainModuleIcons(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "icons"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Custom icons")

    @property
    def icon(self) -> Icon:
        return "icons"

    @property
    def permission(self) -> None | str:
        return "icons"

    @property
    def description(self) -> str:
        return _("Extend the Checkmk GUI with your custom icons")

    @property
    def sort_index(self) -> int:
        return 85

    @property
    def is_show_more(self) -> bool:
        return True
