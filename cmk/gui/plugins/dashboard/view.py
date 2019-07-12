#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.views as views
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.views import PainterOptions

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


@dashlet_registry.register
class ViewDashlet(IFrameDashlet):
    """Dashlet that displays a Check_MK view"""
    @classmethod
    def type_name(cls):
        return "view"

    @classmethod
    def title(cls):
        return _("View")

    @classmethod
    def description(cls):
        return _("Displays the content of a view")

    @classmethod
    def sort_index(cls):
        return 10

    @classmethod
    def initial_size(cls):
        return (40, 20)

    @classmethod
    def vs_parameters(cls):
        def _render_input(dashlet):
            # TODO: Don't modify the self._dashlet data structure here!
            views.transform_view_to_valuespec_value(dashlet)
            return views.render_view_config(dashlet)

        def _handle_input(ident, dashlet):
            dashlet['name'] = 'dashlet_%d' % ident
            dashlet.setdefault('title', _('View'))
            return views.create_view_from_valuespec(dashlet, dashlet)

        return _render_input, _handle_input

    @classmethod
    def add_url(cls):
        return 'create_view_dashlet.py?name=%s&back=%s' % \
            (html.urlencode(html.request.var('name')), html.urlencode(html.makeuri([('edit', '1')])))

    def update(self):
        is_reload = html.request.has_var("_reload")

        display_options = "SIXLW"
        if not is_reload:
            display_options += "HR"

        html.request.set_var('display_options', display_options)
        html.request.set_var('_display_options', display_options)
        html.add_body_css_class('dashlet')

        painter_options = PainterOptions.get_instance()
        painter_options.load(self._dashlet_spec["name"])

        view = views.View(self._dashlet_spec["name"], self._dashlet_spec)
        view.row_limit = views.get_limit()
        view.only_sites = views.get_only_sites()
        view.user_sorters = views.get_user_sorters()

        view_renderer = views.GUIViewRenderer(view, show_buttons=False)
        views.show_view(view, view_renderer)
