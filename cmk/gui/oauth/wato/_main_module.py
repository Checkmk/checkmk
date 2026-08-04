#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override"

from cmk.gui.i18n import _
from cmk.gui.oauth.wato._registered_clients_mode import ModeRegisteredOAuthClients
from cmk.gui.type_defs import DynamicIcon, IconNames, StaticIcon
from cmk.gui.wato import MainModuleTopicGeneral
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic


def register(main_module_registry: MainModuleRegistry) -> None:
    main_module_registry.register(MainModuleRegisteredOAuthClients)


class MainModuleRegisteredOAuthClients(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return ModeRegisteredOAuthClients.name()

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("Registered OAuth clients")

    @property
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODO: add proper icon

    @property
    def permission(self) -> None | str:
        return "users"

    @property
    def description(self) -> str:
        return _("View and delete OAuth clients that dynamically registered themselves.")

    @property
    def sort_index(self) -> int:
        return 90

    @property
    def is_show_more(self) -> bool:
        return True
