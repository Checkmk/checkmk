#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.gui import site_config
from cmk.gui.config import active_config
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import (
    MainMenu,
    MainMenuData,
    MainMenuVueApp,
)
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.userdb.store import load_custom_attr
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.wato.pages.activate_changes import get_last_wato_snapshot_file
from cmk.shared_typing.changes import ChangesProps, NavbarChangesActionChoices


@dataclass
class ActivateChangesData(ChangesProps, MainMenuData): ...


def _hide_menu() -> bool:
    if not user.may("wato.activate"):
        return True
    return (
        site_config.is_distributed_setup_remote_site(active_config.sites)
        and not active_config.wato_enabled
    )


def _get_navbar_changes_action(user: LoggedInUser) -> NavbarChangesActionChoices | None:
    assert user.id is not None
    raw = load_custom_attr(
        user_id=user.id,
        key="navbar_changes_action",
        parser=lambda x: None if x == "None" else x,
    )
    return NavbarChangesActionChoices(raw) if raw is not None else None


def _data(request: Request) -> ActivateChangesData:
    return ActivateChangesData(
        activate_changes_url=makeuri_contextless(
            request,
            vars_=[("mode", "changelog")],
            filename="wato.py",
        ),
        user_has_activate_foreign=user.may("wato.activateforeign"),
        new_installation=get_last_wato_snapshot_file(debug=False) is None,
        user_name=user.ident,
        navbar_changes_action=_get_navbar_changes_action(user),
    )


def register(mega_menu_registry: MainMenuRegistry) -> None:
    mega_menu_registry.register(
        MainMenu(
            name="changes",
            title=_l("Changes"),
            icon=StaticIcon(IconNames.main_changes),
            sort_index=17,
            topics=None,
            hide=_hide_menu,
            vue_app=MainMenuVueApp(
                name="cmk-main-menu-changes",
                data=_data,
            ),
        )
    )
