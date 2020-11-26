#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import DropdownChoice

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


@dashlet_registry.register
class SnapinDashlet(IFrameDashlet):
    """Dashlet that displays a sidebar snapin"""
    @classmethod
    def type_name(cls):
        return "snapin"

    @classmethod
    def title(cls):
        return _("Sidebar Snapin")

    @classmethod
    def description(cls):
        return _("Displays a sidebar snapin.")

    @classmethod
    def sort_index(cls):
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
            ("snapin",
             DropdownChoice(
                 title=_("Snapin"),
                 help=_("Choose the snapin you would like to show."),
                 choices=cls._snapin_choices,
             )),
        ]

    @classmethod
    def _snapin_choices(cls):
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel
        return sorted([(k, v.title()) for k, v in sidebar.snapin_registry.items()],
                      key=lambda x: x[1])

    def display_title(self):
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel
        title = sidebar.snapin_registry[self._dashlet_spec["snapin"]].title()
        return self._dashlet_spec.get("title", title)

    def update(self):
        import cmk.gui.sidebar as sidebar  # pylint: disable=import-outside-toplevel
        dashlet = self._dashlet_spec
        snapin = sidebar.snapin_registry.get(self._dashlet_spec['snapin'])
        if not snapin:
            raise MKUserError(None, _('The configured snapin does not exist.'))
        snapin_instance = snapin()

        html.set_browser_reload(self.refresh_interval())
        html.html_head(_('Snapin Dashlet'))
        html.open_body(class_="side")
        html.open_div(id_="check_mk_sidebar")
        html.open_div(id_="side_content")
        html.open_div(id_="snapin_container_%s" % dashlet['snapin'], class_="snapin")
        html.open_div(id_="snapin_%s" % dashlet['snapin'], class_="content")
        styles = snapin_instance.styles()
        if styles:
            html.style(styles)
        snapin_instance.show()
        html.close_div()
        html.close_div()
        html.close_div()
        html.close_div()
        html.body_end()
