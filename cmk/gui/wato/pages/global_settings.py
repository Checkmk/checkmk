#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Redirects from the retired global settings modes to the pages replacing them"""

import abc
from collections.abc import Collection
from typing import override

from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import request
from cmk.gui.type_defs import ActionResult
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.urls import HTTPVariable, makeuri_contextless


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeEditGlobals)
    mode_registry.register(ModeEditGlobalSetting)
    mode_registry.register(ModeEditSiteGlobals)
    mode_registry.register(ModeEditSiteGlobalSetting)
    mode_registry.register(ModeEventConsoleSettings)
    mode_registry.register(ModeEventConsoleEditGlobalSetting)


def _settings_page_url(filename: str, *carried_variables: str) -> str:
    variables: list[HTTPVariable] = [
        (name, value)
        for name in carried_variables
        if (value := request.get_ascii_input(name)) is not None
    ]
    return makeuri_contextless(request, variables, filename=filename)


class ABCSettingsPageRedirect(WatoMode):
    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return []

    @abc.abstractmethod
    def _target_url(self) -> str:
        raise NotImplementedError

    @override
    def action(self, config: Config) -> ActionResult:
        raise HTTPRedirect(self._target_url())

    @override
    def page(self, config: Config) -> None:
        raise HTTPRedirect(self._target_url())


class ModeEditGlobals(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "globalvars"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("global_settings.py")


class ModeEditGlobalSetting(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_configvar"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("global_settings.py", "varname")


class ModeEditSiteGlobals(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_site_globals"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("site_specific_settings.py", "site")


class ModeEditSiteGlobalSetting(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_site_configvar"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("site_specific_settings.py", "site", "varname")


class ModeEventConsoleSettings(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "mkeventd_config"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("event_console_settings.py")


class ModeEventConsoleEditGlobalSetting(ABCSettingsPageRedirect):
    @classmethod
    @override
    def name(cls) -> str:
        return "mkeventd_edit_configvar"

    @override
    def _target_url(self) -> str:
        return _settings_page_url("event_console_settings.py", "varname")
