#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Collection
from typing import override

from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.type_defs import PermissionName
from cmk.gui.watolib.mode import ModeRegistry, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeNotImplemented)


class ModeNotImplemented(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return ""

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return []

    @override
    def title(self) -> str:
        return _("Error")

    @override
    def page(self, config: Config) -> None:
        html.show_error(_("This module has not yet been implemented."))
