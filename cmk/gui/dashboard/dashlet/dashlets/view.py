#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Callable, Sequence
from typing import cast, Literal, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.gui import visuals
from cmk.gui.config import active_config
from cmk.gui.dashboard.dashlet.base import IFrameDashlet
from cmk.gui.dashboard.type_defs import DashletConfig, DashletId, DashletSize
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import (
    ColumnSpec,
    HTTPVariables,
    InventoryJoinMacrosSpec,
    SingleInfos,
    SorterSpec,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.urls import makeuri, makeuri_contextless, requested_file_name, urlencode
from cmk.gui.valuespec import DictionaryEntry, DropdownChoice
from cmk.gui.view import View
from cmk.gui.view_renderer import GUIViewRenderer
from cmk.gui.views.page_edit_view import create_view_from_valuespec, render_view_config
from cmk.gui.views.page_show_view import get_limit, get_user_sorters, process_view
from cmk.gui.views.store import get_all_views, get_permitted_views
from cmk.gui.views.view_choices import view_choices
from cmk.gui.visuals import get_only_sites_from_context


class ABCViewDashletConfig(DashletConfig):
    name: str


VT = TypeVar("VT", bound=ABCViewDashletConfig)


class LinkedViewDashletConfig(ABCViewDashletConfig): ...


class _ViewDashletConfigMandatory(ABCViewDashletConfig):
    # These fields are redundant between DashletConfig and Visual
    # name: str
    # context: VisualContext
    # single_infos: SingleInfos
    # title: str | LazyString
    add_context_to_title: bool
    sort_index: int
    is_show_more: bool
    # From: ViewSpec
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: list[ColumnSpec]
    painters: list[ColumnSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup", "repeat"]
    sorters: Sequence[SorterSpec]


class ViewDashletConfig(_ViewDashletConfigMandatory, total=False):
    # From: ViewSpec
    add_headers: str
    # View editor only adds them in case they are truish. In our built-in specs these flags are also
    # partially set in case they are falsy
    mobile: bool
    mustsearch: bool
    force_checkboxes: bool
    play_sounds: bool
    user_sortable: bool
    inventory_join_macros: InventoryJoinMacrosSpec


def copy_view_into_dashlet(
    dashlet: ViewDashletConfig,
    nr: int,
    view_name: str,
    add_context: VisualContext | None = None,
    load_from_all_views: bool = False,
) -> None:
    permitted_views = get_permitted_views()

    # it is random which user is first accessing
    # an apache python process, initializing the dashboard loading and conversion of
    # old dashboards. In case of the conversion we really try hard to make the conversion
    # work in all cases. So we need all views instead of the views of the user.
    if load_from_all_views and view_name not in permitted_views:
        # This is not really 100% correct according to the logic of visuals.available(),
        # but we do this for the rare edge case during legacy dashboard conversion, so
        # this should be sufficient
        for (_unused, n), this_view in get_all_views().items():
            # take the first view with a matching name
            if view_name == n:
                view = this_view
                break

        if not view:
            raise MKGeneralException(
                _(
                    "Failed to convert a built-in dashboard which is referencing "
                    'the view "%s". You will have to migrate it to the new '
                    "dashboard format on your own to work properly."
                )
                % view_name
            )
    else:
        view = permitted_views[view_name]

    view = copy.deepcopy(view)  # Clone the view

    # the view definition may contain lazy strings that will be serialized to 'l"to translate"' when
    # saving the view data structure. Which will later cause an SyntaxError when trying to load the
    # .mk file. Resolve these strings here to prevent that issue.
    view["title"] = str(view["title"])
    view["description"] = str(view["description"])

    # TODO: Can hopefully be claned up once view is also a TypedDict
    dashlet.update(view)  # type: ignore[typeddict-item]
    if add_context:
        dashlet["context"] = {**dashlet["context"], **add_context}

    # Overwrite the views default title with the context specific title
    dashlet["title"] = visuals.visual_title("view", view, dashlet["context"])
    # TODO: Shouldn't we use the self._dashlet_context_vars() here?
    name_part: HTTPVariables = [("view_name", view_name)]
    singlecontext_vars = cast(
        HTTPVariables,
        list(
            visuals.get_singlecontext_vars(
                view["context"],
                view["single_infos"],
            ).items()
        ),
    )
    dashletcontext_vars = visuals.context_to_uri_vars(dashlet["context"])
    dashlet["title_url"] = makeuri_contextless(
        request,
        name_part + singlecontext_vars + dashletcontext_vars,
        filename="view.py",
    )

    dashlet["type"] = "view"
    dashlet["name"] = "dashlet_%d" % nr
    dashlet["show_title"] = True
    dashlet["mustsearch"] = False


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

    def _show_view_as_dashlet(
        self, view_spec: ViewSpec | ViewDashletConfig, *, debug: bool
    ) -> None:
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
        # context of dashlet has to be merged after view context, otherwise the
        # context of the view is always used
        context = visuals.get_merged_context(view_context, self.context)

        # We are only interested in the ViewSpec specific attributes here. Once we have the full
        # picture (dashlets typed (already done) and reports typed), we can better decide how to do
        # it
        view = View(self._dashlet_spec["name"], view_spec, context)  # type: ignore[arg-type]
        view.row_limit = get_limit()
        view.only_sites = get_only_sites_from_context(context)
        view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)

        process_view(
            GUIViewRenderer(
                view,
                show_buttons=False,
                page_menu_dropdowns_callback=lambda x, y, z: None,
            ),
            debug=debug,
        )

        html.close_div()

    def _get_infos_from_view_spec(self, view_spec: ViewSpec | ViewDashletConfig) -> SingleInfos:
        ds_name = view_spec["datasource"]
        return data_source_registry[ds_name]().infos


class ViewDashlet(ABCViewDashlet[ViewDashletConfig]):
    """Dashlet that displays a Checkmk view"""

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
            render_view_config(view_spec_from_view_dashlet(dashlet))

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

            return create_view_from_valuespec(old_dashlet, dashlet)

        return _render_input, _handle_input

    @classmethod
    def add_url(cls):
        return "create_view_dashlet.py?name={}&mode=create&back={}".format(
            urlencode(request.var("name")),
            urlencode(makeuri(request, [("edit", "1")])),
        )

    @classmethod
    def default_settings(cls) -> dict[str, object]:
        return {
            "datasource": request.get_str_input_mandatory("datasource"),
            "group_painters": [],
            "layout": "table",
            "painters": [],
            "sorters": [],
            "title": "",
            "browser_reload": 0,
            "column_headers": "off",
            "hidden": False,
            "mustsearch": False,
            "name": "",
            "num_columns": 3,
            "play_sounds": False,
            "sort_index": 99,
            "add_context_to_title": True,
            "is_show_more": False,
        }

    def update(self):
        self._show_view_as_dashlet(self._dashlet_spec, debug=active_config.debug)
        html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def infos(self) -> SingleInfos:
        # Hack for create mode of dashlet editor. The user first selects a datasource and then the
        # single contexts, the dashlet editor needs to use these information.
        if requested_file_name(request) == "edit_dashlet" and request.has_var("datasource"):
            ds_name = request.get_str_input_mandatory("datasource")
            return list(data_source_registry[ds_name]().infos)  # TODO: Hmmm...

        return self._get_infos_from_view_spec(self._dashlet_spec)


def view_spec_from_view_dashlet(dashlet: ViewDashletConfig) -> ViewSpec:
    """Should be aligned with copy_view_into_dashlet"""
    # Sadly there is currently no less verbose way of doing this
    view_spec = ViewSpec(
        {
            "datasource": dashlet["datasource"],
            "group_painters": dashlet["group_painters"],
            "layout": dashlet["layout"],
            "painters": dashlet["painters"],
            "single_infos": dashlet["single_infos"],
            "context": dashlet["context"],
            "sorters": dashlet["sorters"],
            "title": dashlet["title"],
            "browser_reload": dashlet["browser_reload"],
            "column_headers": dashlet["column_headers"],
            "name": dashlet["name"],
            "num_columns": dashlet["num_columns"],
            "sort_index": dashlet["sort_index"],
            "add_context_to_title": dashlet["add_context_to_title"],
            "is_show_more": dashlet["is_show_more"],
            # Add the following NotRequired ViewSpec values here, so they are correctly displayed
            # when editing a builtin dashboard's view dashlet
            "mobile": dashlet.get("mobile", False),
            "mustsearch": dashlet.get("mustsearch", False),
            "force_checkboxes": dashlet.get("force_checkboxes", False),
            "user_sortable": dashlet.get("user_sortable", False),
            "play_sounds": dashlet.get("play_sounds", False),
            # Just to satisfy ViewSpec, not saved to storage and not needed for
            # rendering in a ViewDashlet.
            "owner": UserId.builtin(),
            "description": "",
            "topic": "",
            "icon": None,
            "hidden": False,
            "hidebutton": False,
            "public": False,
            "link_from": {},
            "packaged": False,
            "main_menu_search_terms": [],
        }
    )
    if inventory_join_macros := dashlet.get("inventory_join_macros"):
        view_spec["inventory_join_macros"] = inventory_join_macros
    return view_spec


class LinkedViewDashlet(ABCViewDashlet[LinkedViewDashletConfig]):
    """Dashlet that displays a Checkmk view without embedding it's definition into the dashboard"""

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
                    choices=view_choices,
                    sorted=True,
                ),
            ),
        ]

    @classmethod
    def add_url(cls) -> str:
        return "create_link_view_dashlet.py?name={}&mode=create&back={}".format(
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
        return visuals.visual_title("view", self._get_view_spec(), self.context)

    def title_url(self) -> str:
        view_name = self._dashlet_spec["name"]
        request_vars: HTTPVariables = [("view_name", view_name)]
        request_vars += self._dashlet_context_vars()
        return makeuri_contextless(request, request_vars, filename="view.py")

    def update(self) -> None:
        self._show_view_as_dashlet(self._get_view_spec(), debug=active_config.debug)
        html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def infos(self) -> SingleInfos:
        return self._get_infos_from_view_spec(self._get_view_spec())
