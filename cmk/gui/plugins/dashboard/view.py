#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.views as views
import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.views import PainterOptions
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.exceptions import MKUserError

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


class ABCViewDashlet(IFrameDashlet):
    @classmethod
    def sort_index(cls):
        return 10

    @classmethod
    def initial_size(cls):
        return (40, 20)

    @classmethod
    def has_context(cls):
        return True

    def _show_view_as_dashlet(self, view_spec):
        is_reload = html.request.has_var("_reload")

        display_options = "SIXLW"
        if not is_reload:
            display_options += "HR"

        html.request.set_var('display_options', display_options)
        html.request.set_var('_display_options', display_options)
        html.add_body_css_class('dashlet')

        painter_options = PainterOptions.get_instance()
        painter_options.load(self._dashlet_spec["name"])

        view = views.View(self._dashlet_spec["name"], view_spec, self.context)
        view.row_limit = views.get_limit()
        view.only_sites = visuals.get_only_sites_from_context(self.context)
        view.user_sorters = views.get_user_sorters()

        view_renderer = views.GUIViewRenderer(view, show_buttons=False)
        views.process_view(view, view_renderer)

    def _get_infos_from_view_spec(self, view_spec):
        ds_name = view_spec["datasource"]
        return views.data_source_registry[ds_name]().infos


@dashlet_registry.register
class ViewDashlet(ABCViewDashlet):
    """Dashlet that displays a Check_MK view"""
    @classmethod
    def type_name(cls):
        return "view"

    @classmethod
    def title(cls):
        return _("View")

    @classmethod
    def description(cls):
        return _("Copies a view to a dashlet")

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
        return 'create_view_dashlet.py?name=%s&mode=create&back=%s' % \
            (html.urlencode(html.request.var('name')),
             html.urlencode(html.makeuri([('edit', '1')])))

    def update(self):
        self._show_view_as_dashlet(self._dashlet_spec)

    def infos(self):
        # Hack for create mode of dashlet editor. The user first selects a datasource and then the
        # single contexts, the dashlet editor needs to use these information.
        if html.myfile == "edit_dashlet" and html.request.has_var("datasource"):
            ds_name = html.request.get_str_input_mandatory('datasource')
            return views.data_source_registry[ds_name]().infos

        return self._get_infos_from_view_spec(self._dashlet_spec)


@dashlet_registry.register
class LinkedViewDashlet(ABCViewDashlet):
    """Dashlet that displays a Check_MK view without embedding it's definition into the dashboard"""
    @classmethod
    def type_name(cls):
        return "linked_view"

    @classmethod
    def title(cls):
        return _("Link existing view")

    @classmethod
    def description(cls):
        return _("Displays the content of a view")

    @classmethod
    def vs_parameters(cls):
        return [
            (
                "name",
                DropdownChoice(
                    title=_("View name"),
                    help=
                    _("Choose the view you would like to show. Please note that, depending on the, "
                      "logged in user viewing this dashboard, the view being displayed may "
                      "differ. For example when another user has created a view with the same name. "
                      "In case a user is not permitted to see a view, an error message will be "
                      "displayed."),
                    choices=views.view_choices,
                    sorted=True,
                ),
            ),
        ]

    @classmethod
    def add_url(cls):
        return 'create_link_view_dashlet.py?name=%s&mode=create&back=%s' % \
            (html.urlencode(html.request.var('name')),
             html.urlencode(html.makeuri([('edit', '1')])))

    def _get_view_spec(self):
        view_name = self._dashlet_spec["name"]
        view_spec = views.get_permitted_views().get(view_name)
        if not view_spec:
            raise MKUserError("name", _("No view defined with the name '%s'.") % view_name)

        return view_spec

    def display_title(self):
        return visuals.visual_title("view", self._get_view_spec())

    def title_url(self):
        view_name = self._dashlet_spec["name"]
        return html.makeuri_contextless([('view_name', view_name)] + self._dashlet_context_vars(),
                                        filename='view.py')

    def update(self):
        self._show_view_as_dashlet(self._get_view_spec())

    def infos(self):
        return self._get_infos_from_view_spec(self._get_view_spec())
