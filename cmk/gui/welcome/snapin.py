#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import override

from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.sidebar import SidebarSnapin, SnapinRegistry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.welcome.pages import get_welcome_data, WELCOME_PAGE_PERMISSIONS


def register(snapin_registry: SnapinRegistry) -> None:
    snapin_registry.register(SidebarWelcomeSnapin)


class SidebarWelcomeSnapin(SidebarSnapin):
    @override
    @staticmethod
    def type_name() -> str:
        return "a_welcome"

    @override
    @classmethod
    def title(cls) -> str:
        return _("Welcome to Checkmk")

    @override
    @classmethod
    def description(cls) -> str:
        return _(
            "Stay on track with a quick overview of your setup progress. "
            "The sidebar keeps everything in view, right where you need it."
        )

    @override
    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    @override
    @classmethod
    def may_see(cls, user_permissions: UserPermissions) -> bool:
        if not all(user.may(perm) for perm in WELCOME_PAGE_PERMISSIONS):
            return False
        return True

    @override
    def show(self, config: Config) -> None:
        snapin_props = asdict(get_welcome_data())
        snapin_props.pop("is_start_url", None)
        html.vue_component("cmk-welcome-snapin", data=snapin_props)
