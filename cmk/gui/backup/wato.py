#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.type_defs import Icon
from cmk.gui.wato import MainModuleTopicMaintenance
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleTopic


class MainModuleBackup(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "backup"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    def title(self) -> str:
        return _("Backups")

    @property
    def icon(self) -> Icon:
        return "backup"

    @property
    def permission(self) -> None | str:
        return "backups"

    @property
    def description(self) -> str:
        return _("Make backups of your whole site and restore previous backups.")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False
