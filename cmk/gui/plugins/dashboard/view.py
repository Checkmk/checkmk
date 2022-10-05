#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, TypeVar

import cmk.gui.views as views
import cmk.gui.visuals as visuals
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.plugins.dashboard.utils import (
    ABCViewDashletConfig,
    dashlet_registry,
    DashletId,
    DashletSize,
    IFrameDashlet,
    LinkedViewDashletConfig,
    ViewDashletConfig,
)
from cmk.gui.type_defs import HTTPVariables, SingleInfos, ViewSpec
from cmk.gui.utils.urls import makeuri, makeuri_contextless, requested_file_name, urlencode
from cmk.gui.valuespec import DictionaryEntry, DropdownChoice
from cmk.gui.view import View
from cmk.gui.view_renderer import GUIViewRenderer
from cmk.gui.view_store import get_permitted_views

VT = TypeVar("VT", bound=ABCViewDashletConfig)


class ABCViewDashlet(IFrameDashlet[VT]):
    @classmethod
    def sort_index(cls) -> int:
        return 10

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (40, 20)

    @classmethod
    def has_context(cls) -> bool:
        return True

    def _show_view_as_dashlet(self, view_spec: ViewSpec | ViewDashletConfig) -> None:
        html.add_body_css_class("view")
        html.open_div(id_="dashlet_content_wrapper")

        is_reload = request.has_var("_reload")

        view_display_options = "SIXLW"
        if not is_reload:
            view_display_options += "HR"

        request.set_var("display_options", view_display_options)
        request.set_var("_display_options", view_display_options)
        html.add_body_css_class("dashlet")

        # Need to be loaded before processing the painter_options below.
        # TODO: Make this dependency explicit
        display_options.load_from_html(request, html)

        painter_options = PainterOptions.get_instance()
        painter_options.load(self._dashlet_spec["name"])

        # Here the linked view default context has the highest priority
        # linkedview default>dashlet>url active filter> dashboard. However views
        # have the "show_filters" default to prefill the filtermenu with empty
        # valued filters(UX). Those need to be cleared out. Otherwise those
        # empty filters are the highest priority filters and the user can never
        # filter the view.

        view_context = {
            filtername: filtervalues
            for filtername, filtervalues in view_spec["context"].items()
            if {
                var: value
                for var, value in filtervalues.items()
                # These are the filters request variables. Keep set values
                # For the TriStateFilters unset == ignore == "-1"
                # all other cases unset is an empty string
                if (var.startswith("is_") and value != "-1")  # TriState filters except ignore
                or (not var.startswith("is_") and value)  # Rest of filters with some value
            }
        }
        context = visuals.get_merged_context(self.context, view_context)

        # We are only interested in the ViewSpec specific attributes here. Once we have the full
        # picture (dashlets typed (already done) and reports typed), we can better decide how to do
        # it
        view = View(self._dashlet_spec["name"], view_spec, context)  # type: ignore[arg-type]
        view.row_limit = views.get_limit()
        view.only_sites = visuals.get_only_sites_from_context(context)
        view.user_sorters = views.get_user_sorters()

        views.process_view(GUIViewRenderer(view, show_buttons=False))

        html.close_div()

    def _get_infos_from_view_spec(self, view_spec: ViewSpec | ViewDashletConfig) -> SingleInfos:
        ds_name = view_spec["datasource"]
        return data_source_registry[ds_name]().infos


@dashlet_registry.register
class ViewDashlet(ABCViewDashlet[ViewDashletConfig]):
    """Dashlet that displays a Check_MK view"""

    @classmethod
    def type_name(cls) -> str:
        return "view"

    @classmethod
    def title(cls) -> str:
        return _("View")

    @classmethod
    def description(cls) -> str:
        return _("Copies a view to a dashboard element")

    @classmethod
    def vs_parameters(
        cls,
    ) -> tuple[
        Callable[[ViewDashletConfig], None],
        Callable[[DashletId, ViewDashletConfig, ViewDashletConfig], ViewDashletConfig],
    ]:
        def _render_input(dashlet: ViewDashletConfig) -> None:
            # TODO: Don't modify the self._dashlet data structure here!
            views.transform_view_to_valuespec_value(dashlet)
            # We are only interested in the ViewSpec specific attributes here. Once we have the full
            # picture (dashlets typed (already done) and reports typed), we can better decide how to do
            # it
            views.render_view_config(dashlet)  # type: ignore[arg-type]

        def _handle_input(
            ident: DashletId, old_dashlet: ViewDashletConfig, dashlet: ViewDashletConfig
        ) -> ViewDashletConfig:
            dashlet["name"] = "dashlet_%d" % ident
            dashlet.setdefault("title", _("View"))

            # The view dashlet editor does not provide a configuration for the general visual
            # settings as defined in visuals._vs_general. They have no effect on the dashlets, but
            # let's apply them here for consistency.
            dashlet.setdefault("sort_index", 99)
            dashlet.setdefault("add_context_to_title", True)
            dashlet.setdefault("is_show_more", False)

            return views.create_view_from_valuespec(old_dashlet, dashlet)

        return _render_input, _handle_input

    @classmethod
    def add_url(cls):
        return "create_view_dashlet.py?name=%s&mode=create&back=%s" % (
            urlencode(request.var("name")),
            urlencode(makeuri(request, [("edit", "1")])),
        )

    def update(self):
        self._show_view_as_dashlet(self._dashlet_spec)
        html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def infos(self) -> SingleInfos:
        # Hack for create mode of dashlet editor. The user first selects a datasource and then the
        # single contexts, the dashlet editor needs to use these information.
        if requested_file_name(request) == "edit_dashlet" and request.has_var("datasource"):
            ds_name = request.get_str_input_mandatory("datasource")
            return list(data_source_registry[ds_name]().infos)  # TODO: Hmmm...

        return self._get_infos_from_view_spec(self._dashlet_spec)


@dashlet_registry.register
class LinkedViewDashlet(ABCViewDashlet[LinkedViewDashletConfig]):
    """Dashlet that displays a Check_MK view without embedding it's definition into the dashboard"""

    @classmethod
    def type_name(cls) -> str:
        return "linked_view"

    @classmethod
    def title(cls) -> str:
        return _("Link existing view")

    @classmethod
    def description(cls) -> str:
        return _("Displays the content of a view")

    @classmethod
    def vs_parameters(cls) -> list[DictionaryEntry]:
        return [
            (
                "name",
                DropdownChoice(
                    title=_("View name"),
                    help=_(
                        "Choose the view you would like to show. Please note that, depending on the, "
                        "logged in user viewing this dashboard, the view being displayed may "
                        "differ. For example when another user has created a view with the same name. "
                        "In case a user is not permitted to see a view, an error message will be "
                        "displayed."
                    ),
                    choices=views.view_choices,
                    sorted=True,
                ),
            ),
        ]

    @classmethod
    def add_url(cls) -> str:
        return "create_link_view_dashlet.py?name=%s&mode=create&back=%s" % (
            urlencode(request.var("name")),
            urlencode(makeuri(request, [("edit", "1")])),
        )

    def _get_view_spec(self) -> ViewSpec:
        view_name = self._dashlet_spec["name"]
        view_spec = get_permitted_views().get(view_name)
        if not view_spec:
            raise MKUserError("name", _("No view defined with the name '%s'.") % view_name)

        # Override some view dashlet specific options
        view_spec = view_spec.copy()
        view_spec["user_sortable"] = False

        return view_spec

    def default_display_title(self) -> str:
        return visuals.visual_title("view", dict(self._get_view_spec()), self.context)

    def title_url(self) -> str:
        view_name = self._dashlet_spec["name"]
        request_vars: HTTPVariables = [("view_name", view_name)]
        request_vars += self._dashlet_context_vars()
        return makeuri_contextless(request, request_vars, filename="view.py")

    def update(self) -> None:
        self._show_view_as_dashlet(self._get_view_spec())
        html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def infos(self) -> SingleInfos:
        return self._get_infos_from_view_spec(self._get_view_spec())
