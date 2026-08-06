#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.i18n import _
from cmk.gui.type_defs import DynamicIcon, IconNames, StaticIcon
from cmk.gui.wato import MainModuleTopicExporter
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic


def register(main_module_registry: MainModuleRegistry) -> None:
    main_module_registry.register(MainModuleMicrosoftEntraId)


class MainModuleMicrosoftEntraId(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return "microsoft_entra_id_connections"

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicExporter

    @property
    @override
    def title(self) -> str:
        return _("Microsoft Entra ID connections")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODD: add proper icon

    @property
    @override
    def permission(self) -> None | str:
        return "oauth2_connections"

    @property
    @override
    def description(self) -> str:
        return _("Create Microsoft Entra ID connections.")

    @property
    @override
    def sort_index(self) -> int:
        return 55

    @property
    @override
    def is_show_more(self) -> bool:
        return True
