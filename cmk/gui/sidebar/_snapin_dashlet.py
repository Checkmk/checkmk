#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Iterator
from typing import override

from cmk.gui.config import active_config, Config
from cmk.gui.dashboard import DashletConfig, IFrameDashlet
from cmk.gui.dashboard.type_defs import DashletRefreshInterval, DashletSize
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.valuespec.definitions import DictionaryEntry

from ._snapin import all_snapins, SidebarSnapin


class SnapinDashletConfig(DashletConfig):
    snapin: str


class SnapinDashlet(IFrameDashlet[SnapinDashletConfig]):
    """Dashlet that displays a sidebar snap-in"""

    @classmethod
    def type_name(cls) -> str:
        return "snapin"

    @classmethod
    def title(cls) -> str:
        return _("Sidebar element")

    @classmethod
    def description(cls) -> str:
        return _("Allows you to use a sidebar element in the dashboard.")

    @classmethod
    def sort_index(cls) -> int:
        return 55

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (28, 20)

    @classmethod
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return 30

    @classmethod
    def vs_parameters(cls) -> list[DictionaryEntry]:
        return [
            (
                "snapin",
                DropdownChoice(
                    title=_("Sidebar element"),
                    help=_("Choose the sidebar element you would like to show."),
                    choices=cls._snapin_choices,
                ),
            ),
        ]

    @classmethod
    def _snapin_choices(cls) -> list[tuple[str, str]]:
        return sorted(
            [
                (k, v.title())
                for k, v in all_snapins(
                    UserPermissions.from_config(active_config, permission_registry)
                ).items()
            ],
            key=lambda x: x[1],
        )

    def default_display_title(self) -> str:
        return all_snapins(
            UserPermissions.from_config(active_config, permission_registry),
        )[self._dashlet_spec["snapin"]].title()

    def update(self, config: Config, user_permissions: UserPermissions) -> None:
        dashlet = self._dashlet_spec
        snapin = all_snapins(user_permissions).get(self._dashlet_spec["snapin"])
        if not snapin:
            raise MKUserError(None, _("The configured element does not exist."))
        snapin_instance = snapin()
        snapin_name = dashlet["snapin"]

        html.browser_reload = self.refresh_interval()
        html.html_head(_("Sidebar element"))
        html.open_body(class_="side", data_theme=theme.get())
        html.open_div(id_="check_mk_sidebar")
        html.open_div(id_="side_content")
        show_more = user.get_show_more_setting(f"sidebar_snapin_{snapin_name}")
        html.open_div(
            id_=f"snapin_container_{snapin_name}",
            class_=["snapin", ("more" if show_more else "less")],
        )
        html.open_div(id_="snapin_%s" % dashlet["snapin"], class_="content")
        styles = snapin_instance.styles()
        if styles:
            html.style(styles)
        snapin_instance.show(config)
        html.close_div()
        html.close_div()
        html.close_div()
        html.close_div()
        html.javascript('cmk.utils.add_simplebar_scrollbar("check_mk_sidebar");')
        html.body_end()


class SnapinWidgetIFramePage(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        """Render a snapin for use in an iframe."""
        snapin_name = ctx.request.get_ascii_input_mandatory("name")
        snapin_instance = self._get_snapin_instance(
            snapin_name, UserPermissions.from_config(ctx.config, permission_registry)
        )

        html.browser_reload = False
        html.html_head(_("Sidebar element"))
        html.open_body(class_="side", data_theme=theme.get())
        with self._scrollbar():
            html.open_div(id_="side_content")
            with self._snapin_container(snapin_name):
                self._show_snapin(snapin_instance, ctx.config)
            html.close_div()
        html.body_end()

    @staticmethod
    def _get_snapin_instance(snapin_name: str, user_permissions: UserPermissions) -> SidebarSnapin:
        snapin = all_snapins(user_permissions).get(snapin_name)
        if not snapin:
            raise MKUserError(None, _("The configured element does not exist."))
        return snapin()

    @staticmethod
    @contextlib.contextmanager
    def _scrollbar() -> Iterator[None]:
        html.open_div(id_="check_mk_sidebar")
        try:
            yield None
        finally:
            html.close_div()
            html.javascript('cmk.utils.add_simplebar_scrollbar("check_mk_sidebar");')

    @staticmethod
    @contextlib.contextmanager
    def _snapin_container(snapin_name: str) -> Iterator[None]:
        show_more = user.get_show_more_setting(f"sidebar_snapin_{snapin_name}")
        html.open_div(
            id_=f"snapin_container_{snapin_name}",
            class_=["snapin", ("more" if show_more else "less")],
        )
        try:
            yield None
        finally:
            html.close_div()

    @staticmethod
    def _show_snapin(snapin_instance: SidebarSnapin, config: Config) -> None:
        html.open_div(id_=f"snapin_{snapin_instance.type_name()}", class_="content")
        if styles := snapin_instance.styles():
            html.style(styles)
        snapin_instance.show(config)
        html.close_div()
