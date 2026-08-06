#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.i18n import _
from cmk.gui.type_defs import DynamicIcon, IconNames, StaticIcon
from cmk.gui.wato import MainModuleTopicMaintenance
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleTopic


class MainModuleBackup(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "backup"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicMaintenance

    @property
    @override
    def title(self) -> str:
        return _("Backups")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.backup)

    @property
    @override
    def permission(self) -> None | str:
        return "backups"

    @property
    @override
    def description(self) -> str:
        return _("Make backups of your whole site and restore previous backups.")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @property
    @override
    def is_show_more(self) -> bool:
        return False
