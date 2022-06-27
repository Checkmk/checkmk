#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import dashlet_registry, IFrameDashlet
from cmk.gui.utils.theme import theme
from cmk.gui.valuespec import DropdownChoice


@dashlet_registry.register
class SnapinDashlet(IFrameDashlet):
    """Dashlet that displays a sidebar snapin"""

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
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel

        return sorted(
            [(k, v.title()) for k, v in sidebar.snapin_registry.items()], key=lambda x: x[1]
        )

    def default_display_title(self) -> str:
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel

        return sidebar.snapin_registry[self._dashlet_spec["snapin"]].title()

    def update(self):
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel

        dashlet = self._dashlet_spec
        snapin = sidebar.snapin_registry.get(self._dashlet_spec["snapin"])
        if not snapin:
            raise MKUserError(None, _("The configured element does not exist."))
        snapin_instance = snapin()

        html.browser_reload = self.refresh_interval()
        html.html_head(_("Sidebar element"))
        html.open_body(class_="side", data_theme=theme.get())
        html.open_div(id_="check_mk_sidebar")
        html.open_div(id_="side_content")
        html.open_div(id_="snapin_container_%s" % dashlet["snapin"], class_="snapin")
        html.open_div(id_="snapin_%s" % dashlet["snapin"], class_="content")
        styles = snapin_instance.styles()
        if styles:
            html.style(styles)
        snapin_instance.show()
        html.close_div()
        html.close_div()
        html.close_div()
        html.close_div()
        html.body_end()
