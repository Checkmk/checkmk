#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry
from cmk.gui.valuespec import TextInput


@dashlet_registry.register
class StaticTextDashlet(Dashlet):
    """Dashlet that displays a static text"""

    @classmethod
    def type_name(cls):
        return "nodata"

    @classmethod
    def title(cls):
        return _("Static text")

    @classmethod
    def description(cls):
        return _("Displays a static text to the user.")

    @classmethod
    def sort_index(cls):
        return 100

    @classmethod
    def initial_size(cls):
        return (30, 18)

    @classmethod
    def vs_parameters(cls):
        return [
            (
                "text",
                TextInput(
                    title=_("Text"),
                    size=50,
                    help=_(
                        "You can enter a text here that will be displayed in the element when "
                        "viewing the dashboard. It is also possible to insert a limited set of HTML "
                        "tags, some of them are: h2, b, tt, i, br, pre, a, sup, p, li, ul and ol."
                    ),
                ),
            ),
        ]

    def show(self):
        html.open_div(class_="nodata")
        html.open_div(class_="msg")
        html.write_text(self._dashlet_spec.get("text", ""))
        html.close_div()
        html.close_div()
