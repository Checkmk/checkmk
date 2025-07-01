#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.dashboard import DashletConfig, IFrameDashlet
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.theme.current_theme import theme
from cmk.gui.valuespec import DropdownChoice

from ._snapin import all_snapins


class SnapinDashletConfig(DashletConfig):
    snapin: str


class SnapinDashlet(IFrameDashlet[SnapinDashletConfig]):
    """Dashlet that displays a sidebar snap-in"""

    @classmethod
    def type_name(cls):
        return "snapin"

    @classmethod
    def title(cls):
        return _("Sidebar element")

    @classmethod
    def description(cls):
        return _("Allows you to use a sidebar element in the dashboard.")

    @classmethod
    def sort_index(cls) -> int:
        return 55

    @classmethod
    def initial_size(cls):
        return (28, 20)

    @classmethod
    def initial_refresh_interval(cls):
        return 30

    @classmethod
    def vs_parameters(cls):
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
    def _snapin_choices(cls):
        return sorted([(k, v.title()) for k, v in all_snapins().items()], key=lambda x: x[1])

    def default_display_title(self) -> str:
        return all_snapins()[self._dashlet_spec["snapin"]].title()

    def update(self):
        dashlet = self._dashlet_spec
        snapin = all_snapins().get(self._dashlet_spec["snapin"])
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
        snapin_instance.show(active_config)
        html.close_div()
        html.close_div()
        html.close_div()
        html.close_div()
        html.javascript('cmk.utils.add_simplebar_scrollbar("check_mk_sidebar");')
        html.body_end()
