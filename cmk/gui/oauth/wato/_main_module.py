#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.i18n import _
from cmk.gui.oauth.wato._registered_clients_mode import ModeRegisteredOAuthClients
from cmk.gui.oauth.wato._user_tokens_mode import ModeOAuthTokens
from cmk.gui.wato import MainModuleTopicGeneral
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic
from cmk.web.utils.icons import DynamicIcon, IconNames, StaticIcon


def register(main_module_registry: MainModuleRegistry) -> None:
    main_module_registry.register(MainModuleRegisteredOAuthClients)
    main_module_registry.register(MainModuleOAuthTokens)


class MainModuleRegisteredOAuthClients(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return ModeRegisteredOAuthClients.name()

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("Registered OAuth clients")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODO: add proper icon

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("View and delete OAuth clients that dynamically registered themselves.")

    @property
    @override
    def sort_index(self) -> int:
        return 90

    @property
    @override
    def is_show_more(self) -> bool:
        return True


class MainModuleOAuthTokens(ABCMainModule):
    @property
    @override
    def mode_or_url(self) -> str:
        return ModeOAuthTokens.name()

    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    @override
    def title(self) -> str:
        return _("OAuth access tokens")

    @property
    @override
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODO: add proper icon

    @property
    @override
    def permission(self) -> None | str:
        return "users"

    @property
    @override
    def description(self) -> str:
        return _("View and revoke OAuth access tokens issued to users.")

    @property
    @override
    def sort_index(self) -> int:
        return 91

    @property
    @override
    def is_show_more(self) -> bool:
        return True
