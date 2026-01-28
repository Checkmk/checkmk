#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import DynamicIcon, IconNames, StaticIcon
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.wato import MainModuleTopicExporter, MainModuleTopicGeneral
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic


def register(main_module_registry: MainModuleRegistry) -> None:
    main_module_registry.register(MainModuleOAuth2Connection)
    main_module_registry.register(MainModuleMicrosoftEntraId)


class MainModuleOAuth2Connection(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "oauth2_connections"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicGeneral

    @property
    def title(self) -> str:
        return _("OAuth2 connections")

    @property
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODD: add proper icon

    @property
    def permission(self) -> None | str:
        return "oauth2_connections"

    @property
    def description(self) -> str:
        return _("Create OAuth2 connections.")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return False


class MainModuleMicrosoftEntraId(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return makeuri_contextless(
            request,
            [("mode", "oauth2_connections"), ("connector_type", "microsoft_entra_id")],
            "wato.py",
        )

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicExporter

    @property
    def title(self) -> str:
        return _("Microsoft Entra ID connections")

    @property
    def icon(self) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.passwords)  # TODD: add proper icon

    @property
    def permission(self) -> None | str:
        return "oauth2_connections"

    @property
    def description(self) -> str:
        return _("Create Microsoft Entra ID connections.")

    @property
    def sort_index(self) -> int:
        return 55

    @property
    def is_show_more(self) -> bool:
        return True
