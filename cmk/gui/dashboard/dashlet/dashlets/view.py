#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import copy
import dataclasses
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import cast, get_args, Literal, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.dashboard.dashlet.base import IFrameDashlet
from cmk.gui.dashboard.store import (
    get_all_dashboards,
    get_permitted_dashboards,
    save_all_dashboards,
)
from cmk.gui.dashboard.type_defs import (
    ABCViewDashletConfig,
    DashboardConfig,
    DashletId,
    DashletSize,
    EmbeddedViewDashletConfig,
    LinkedViewDashletConfig,
    ViewDashletConfig,
)
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import Page
from cmk.gui.painter_options import PainterOptions
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import (
    DashboardEmbeddedViewSpec,
    HTTPVariables,
    SingleInfos,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri, makeuri_contextless, requested_file_name, urlencode
from cmk.gui.valuespec import DictionaryEntry, DropdownChoice
from cmk.gui.view import View
from cmk.gui.view_renderer import GUIViewRenderer
from cmk.gui.views.page_edit_view import create_view_from_valuespec, render_view_config
from cmk.gui.views.page_show_view import get_limit, get_user_sorters, process_view
from cmk.gui.views.store import get_all_views, get_permitted_views, get_view_by_name
from cmk.gui.views.view_choices import view_choices
from cmk.gui.visuals import get_only_sites_from_context
from cmk.gui.visuals.info import visual_info_registry

VT = TypeVar("VT", bound=ABCViewDashletConfig)


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
        self,
        view_spec: ViewSpec | ViewDashletConfig,
        user_permissions: UserPermissions,
        *,
        soft_query_limit: int,
        hard_query_limit: int,
        debug: bool,
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
        view = View(
            self._dashlet_spec["name"],
            view_spec,  # type: ignore[arg-type]
            context,
            user_permissions,
        )
        view.row_limit = get_limit(
            request_limit_mode=request.get_ascii_input_mandatory("limit", "soft"),
            soft_query_limit=soft_query_limit,
            may_ignore_soft_limit=user.may("general.ignore_soft_limit"),
            hard_query_limit=hard_query_limit,
            may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
        )
        view.only_sites = get_only_sites_from_context(context)
        view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)

        process_view(
            GUIViewRenderer(
                view,
                show_buttons=False,
                page_menu_dropdowns_callback=lambda x, y, z: None,
            ),
            user_permissions,
            debug=debug,
        )

        html.close_div()

    def _get_infos_from_view_spec(self, view_spec: ViewSpec | ViewDashletConfig) -> SingleInfos:
        ds_name = view_spec["datasource"]
        return data_source_registry[ds_name]().infos


class EmbeddedViewDashlet(ABCViewDashlet[EmbeddedViewDashletConfig]):
    """Dashlet that displays a Checkmk view"""

    @classmethod
    def type_name(cls) -> str:
        return "embedded_view"

    @classmethod
    def title(cls) -> str:
        return _("View")

    @classmethod
    def description(cls) -> str:
        return _("Copies a view to a dashboard element")

    def update(self, config: Config) -> None:
        raise NotImplementedError()


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

    def update(self, config: Config) -> None:
        self._show_view_as_dashlet(
            self._dashlet_spec,
            UserPermissions.from_config(config, permission_registry),
            soft_query_limit=config.soft_query_limit,
            hard_query_limit=config.hard_query_limit,
            debug=config.debug,
        )
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

    def update(self, config: Config) -> None:
        self._show_view_as_dashlet(
            self._get_view_spec(),
            UserPermissions.from_config(config, permission_registry),
            soft_query_limit=config.soft_query_limit,
            hard_query_limit=config.hard_query_limit,
            debug=config.debug,
        )
        html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def infos(self) -> SingleInfos:
        return self._get_infos_from_view_spec(self._get_view_spec())


class EmbeddedViewSpecManager:
    @classmethod
    def get_embedded_view_spec(
        cls, dashboard: DashboardConfig, embedded_id: str, view_name: str
    ) -> ViewSpec:
        embedded_views = dashboard.get("embedded_views", {})
        if embedded_id not in embedded_views:
            raise MKUserError(
                "embedded_id",
                _("The dashboard '%s' does not contain an embedded view with the ID '%s'.")
                % (dashboard["name"], embedded_id),
            )

        return cls.embedded_to_normal_view_spec(
            embedded_views[embedded_id],
            dashboard["owner"],
            name=view_name,
        )

    @classmethod
    def normal_to_embedded_view_spec(cls, spec: ViewSpec) -> DashboardEmbeddedViewSpec:
        embedded = DashboardEmbeddedViewSpec(
            single_infos=spec["single_infos"],
            datasource=spec["datasource"],
            layout=spec["layout"],
            group_painters=spec["group_painters"],
            painters=spec["painters"],
            browser_reload=spec["browser_reload"],
            num_columns=spec["num_columns"],
            column_headers=spec["column_headers"],
            sorters=spec["sorters"],
        )
        cls._copy_optionals(source=spec, target=embedded)
        return embedded

    @classmethod
    def embedded_to_normal_view_spec(
        cls, spec: DashboardEmbeddedViewSpec, dashboard_owner: UserId, name: str
    ) -> ViewSpec:
        view_spec = ViewSpec(
            owner=dashboard_owner,
            name=name,
            single_infos=spec["single_infos"],
            datasource=spec["datasource"],
            layout=spec["layout"],
            group_painters=spec["group_painters"],
            painters=spec["painters"],
            sorters=spec["sorters"],
            browser_reload=spec["browser_reload"],
            num_columns=spec["num_columns"],
            column_headers=spec["column_headers"],
            context={},
            add_context_to_title=False,
            title="",
            description="",
            topic="",
            sort_index=0,
            is_show_more=False,
            icon=None,
            hidden=False,
            hidebutton=False,
            public=False,
            packaged=False,
            link_from={},
            main_menu_search_terms=[],
        )
        cls._copy_optionals(source=spec, target=view_spec)
        return view_spec

    @staticmethod
    def _copy_optionals(
        source: ViewSpec | DashboardEmbeddedViewSpec, target: ViewSpec | DashboardEmbeddedViewSpec
    ) -> None:
        if add_headers := source.get("add_headers"):
            target["add_headers"] = add_headers
        if mobile := source.get("mobile"):
            target["mobile"] = mobile
        if mustsearch := source.get("mustsearch"):
            target["mustsearch"] = mustsearch
        if force_checkboxes := source.get("force_checkboxes"):
            target["force_checkboxes"] = force_checkboxes
        if play_sounds := source.get("play_sounds"):
            target["play_sounds"] = play_sounds
        if inventory_join_macros := source.get("inventory_join_macros"):
            target["inventory_join_macros"] = inventory_join_macros


class ViewWidgetIFramePage(Page):
    def page(self, config: Config) -> None:
        """Render a single view for use in an iframe.

        This needs to support two modes:
            1. Render an existing linked view, identified by its name
            2. Render a view that's embedded in the dashboard config, identified by its internal ID
        """
        dashboard_name = request.get_ascii_input_mandatory("dashboard")
        widget_id = request.get_ascii_input_mandatory("widget_id")
        is_reload = request.var("display_options", request.var("_display_options")) is not None
        is_debug = request.var("debug") == "1"
        view_spec = self._get_view_spec(dashboard_name)
        context = self._get_context()
        widget_unique_name = f"{dashboard_name}_{widget_id}"
        self._setup_display_and_painter_options(widget_unique_name, is_reload)

        # filled_in needs to be set in order for rows to be fetched, so we set it to a default here
        if request.var("filled_in") is None:
            request.set_var("filled_in", "filter")

        user_permissions = UserPermissions.from_config(config, permission_registry)
        view = View(
            widget_unique_name,
            view_spec,
            context,
            user_permissions=user_permissions,
        )
        view.row_limit = get_limit(
            request_limit_mode=request.get_ascii_input_mandatory("limit", "soft"),
            soft_query_limit=config.soft_query_limit,
            may_ignore_soft_limit=user.may("general.ignore_soft_limit"),
            hard_query_limit=config.hard_query_limit,
            may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
        )
        view.only_sites = get_only_sites_from_context(context)
        view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)

        with self._wrapper_context(is_reload):
            process_view(
                GUIViewRenderer(
                    view,
                    show_buttons=False,
                    page_menu_dropdowns_callback=lambda x, y, z: None,
                ),
                user_permissions=user_permissions,
                debug=is_debug,
            )

    def _wrapper_context(self, is_reload: bool) -> contextlib.AbstractContextManager[None]:
        if not is_reload:
            return self._content_wrapper()

        return contextlib.nullcontext()

    @staticmethod
    @contextlib.contextmanager
    def _content_wrapper() -> Iterator[None]:
        html.add_body_css_class("view")
        html.add_body_css_class("dashlet")
        html.open_div(id_="dashlet_content_wrapper")
        try:
            yield None
        finally:
            html.close_div()
            html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')

    def _get_view_spec(self, dashboard_name: str) -> ViewSpec:
        """Return the requested view spec, either embedded in the dashboard or a normal view."""
        if embedded_id := request.get_str_input("embedded_id"):
            view_spec = self._get_embedded_view_spec(dashboard_name, embedded_id)
        else:
            view_spec = self._get_linked_view_spec()

        # Override some view widget specific options
        view_spec = view_spec.copy()
        view_spec["user_sortable"] = False

        return view_spec

    @staticmethod
    def _get_linked_view_spec() -> ViewSpec:
        view_name = request.get_ascii_input_mandatory("view_name")
        view_spec = get_permitted_views().get(view_name)
        if not view_spec:
            raise MKUserError("name", _("No view defined with the name '%s'.") % view_name)

        return view_spec

    @staticmethod
    def _get_embedded_view_spec(dashboard_name: str, embedded_id: str) -> ViewSpec:
        dashboards = get_permitted_dashboards()
        if dashboard_name not in dashboards:
            raise MKUserError(
                "dashboard",
                _("The dashboard '%s' does not exist or you do not have permission to view it.")
                % dashboard_name,
            )

        return EmbeddedViewSpecManager.get_embedded_view_spec(
            dashboards[dashboard_name], embedded_id, f"{dashboard_name}_{embedded_id}"
        )

    @staticmethod
    def _setup_display_and_painter_options(dashlet_name: str, is_reload: bool) -> None:
        if not is_reload:
            view_display_options = "HRSIXLW"

            request.set_var("display_options", view_display_options)
            request.set_var("_display_options", view_display_options)

        # Need to be loaded before processing the painter_options below.
        # TODO: Make this dependency explicit
        display_options.load_from_html(request, html)

        painter_options = PainterOptions.get_instance()
        painter_options.load(dashlet_name)

    @staticmethod
    def _get_context() -> VisualContext:
        context = json.loads(request.get_ascii_input_mandatory("context"))
        return {
            filter_name: filter_values
            for filter_name, filter_values in context.items()
            # only include filters which have at least one set value
            if {
                var: value
                for var, value in filter_values.items()
                # These are the filters request variables. Keep set values
                # For the TriStateFilters unset == ignore == "-1"
                # all other cases unset is an empty string
                if (var.startswith("is_") and value != "-1")  # TriState filters except ignore
                or (not var.startswith("is_") and value)  # Rest of filters with some value
            }
        }


class ViewWidgetEditPage(Page):
    type Mode = Literal["create", "copy", "edit"]

    @dataclass(kw_only=True, slots=True)
    class ConfigurationErrorMessage:
        type: Literal["cmk:view:configuration-error"] = "cmk:view:configuration-error"
        message: str

    @dataclass(kw_only=True, slots=True)
    class ValidationErrorMessage:
        type: Literal["cmk:view:validation-error"] = "cmk:view:validation-error"

    @dataclass(kw_only=True, slots=True)
    class SaveCompletedMessage:
        type: Literal["cmk:view:save-completed"] = "cmk:view:save-completed"
        datasource: str
        single_infos: SingleInfos

    def page(self, config: Config) -> None:
        """Render the view editor for embedded views in dashboards.

        This reuses the existing view editor, but should only show the view specific fields.
        The page is expected to be used in an iframe, so it should not render any header.

        The page supports three modes:
            - create: Create a new embedded view from scratch. Requires the datasource and
                      single_infos query args.
            - copy: Create a new embedded view by copying an existing view. Requires the view_name
                    query arg.
            - edit: Edit an existing embedded view.

        In addition, the following query args are always used:
            - mode: The mode of the editor, one of "create", "copy", "edit".
            - dashboard: The name of the dashboard the view is embedded in.
            - owner: The owner of the dashboard. Must match the logged-in user, unless the user
                     has the `general.edit_foreign_dashboards` permission and the mode is "edit".
            - embedded_id: The internal ID of the embedded view in the dashboard. Must be generated
                           on the client side even for new views.

        The page communicates with the parent window via the JavaScript postMessage function.
        It sends the following messages:
            - Configuration error: Sent when the page cannot be rendered due to missing or invalid
                                   query args. The message contains a human-readable error message.
            - Validation error: Sent when the user tries to save the view, but the validation fails.
                                The user can then fix the error and try again. Used to re-enable the
                                save button in the parent window.
            - Save completed: Sent when the user successfully saves the view. The parent window can
                              then close the editor and proceed to the next step.

        This page is expected to contain a hidden save button with the name "_save", which will be
        interacted with via JavaScript from the parent window.
        """
        try:
            user.need_permission("general.edit_dashboards")
            dashboard_name = request.get_ascii_input_mandatory("dashboard")
            embedded_id = request.get_ascii_input_mandatory("embedded_id")
            mode = self._get_mode()
            owner = self._get_owner(mode)

            dashboard = self._load_dashboard(owner, dashboard_name)
            view_spec = self._get_view_spec(dashboard, embedded_id, mode)
        except (MKUserError, MKAuthException) as e:
            # we can't render the view editor with invalid input, notify the parent window
            self._post_message(self.ConfigurationErrorMessage(message=str(e)))
            return  # nothing the user can do, stop rendering the rest

        error = None
        if request.var("_save"):
            try:
                self._save(dashboard, embedded_id, view_spec)
            except MKUserError as e:
                error = e
            else:
                # on save, we only want to notify the parent that we're done
                # this is handled on the dashboard view workflow side
                # because of the copy mode, we need to send back the data source and single infos
                self._post_message(
                    self.SaveCompletedMessage(
                        datasource=view_spec["datasource"], single_infos=view_spec["single_infos"]
                    )
                )
                return  # we're done, stop rendering the rest

        html.body_start()  # include CSS to render the view editor properly
        # remove the 10px padding that body.main adds
        html.open_div(style="margin-left: -10px;")
        if error:
            html.show_error(str(error))
            # we need to let the frontend know that the save failed
            self._post_message(self.ValidationErrorMessage())

        with html.form_context("widget_view", method="POST"):
            # we use the hidden "_save" button via the parent windows javascript

            html.hidden_field("dashboard", dashboard_name)
            html.hidden_field("embedded_id", embedded_id)
            html.hidden_field("datasource", view_spec["datasource"])
            html.hidden_field("single_infos", ",".join(view_spec["single_infos"]))
            html.hidden_field("mode", "edit" if mode == "edit" else "create")  # copy -> create
            html.hidden_field("owner", str(owner))

            render_view_config(view_spec, general_properties=True)

        html.close_div()
        html.body_end()

    @staticmethod
    def _post_message(
        message: ConfigurationErrorMessage | ValidationErrorMessage | SaveCompletedMessage,
    ) -> None:
        serialized = dataclasses.asdict(message)
        html.javascript(f"window.parent.postMessage({serialized!r})")

    @staticmethod
    def _save(dashboard: DashboardConfig, embedded_id: str, view_spec: ViewSpec) -> None:
        # first arg is just used for the datasource (so it can't be overwritten)
        view_spec = create_view_from_valuespec(old_view=view_spec, view=view_spec)
        embedded = EmbeddedViewSpecManager.normal_to_embedded_view_spec(view_spec)
        dashboard.setdefault("embedded_views", {})[embedded_id] = embedded
        save_all_dashboards()
        # we don't do the remote site sync here, as this is done when the dashboard is saved
        # we accept that this might drift apart for now

    @staticmethod
    def _get_mode() -> Mode:
        mode = request.get_ascii_input_mandatory("mode")
        if mode not in get_args(ViewWidgetEditPage.Mode.__value__):
            raise MKUserError("mode", _("Invalid mode '%s'.") % mode)
        return cast(ViewWidgetEditPage.Mode, mode)

    @staticmethod
    def _get_owner(mode: Mode) -> UserId:
        owner_id = request.get_validated_type_input_mandatory(UserId, "owner", user.id)
        if owner_id != user.id:
            if mode == "edit":
                # we're editing views that are saved inside the dashboard config
                if not user.may("general.edit_foreign_dashboards"):
                    raise MKAuthException(
                        _("You are not allowed to edit foreign %s.") % "dashboards"
                    )
            else:  # create/copy mode
                raise MKAuthException(_("Mismatching owner in `%s` mode.") % mode)
        return owner_id

    @staticmethod
    def _get_datasource_from_request() -> str:
        datasource = request.get_ascii_input_mandatory("datasource")
        if datasource not in data_source_registry:
            raise MKUserError("datasource", _("The datasource '%s' does not exist.") % datasource)

        return datasource

    @staticmethod
    def _get_single_infos_from_request() -> SingleInfos:
        single_infos_str = request.get_str_input("single_infos")
        if not single_infos_str:
            return []

        single_infos: SingleInfos = single_infos_str.split(",")
        for key in single_infos:
            if key not in visual_info_registry:
                raise MKUserError("single_infos", _("The info %s does not exist.") % key)

        return single_infos

    @staticmethod
    def _get_original_view_spec_from_request() -> ViewSpec:
        view_name = request.get_ascii_input_mandatory("view_name")
        return get_view_by_name(view_name)

    @staticmethod
    def _load_dashboard(owner: UserId, dashboard_name: str) -> DashboardConfig:
        # loading via get_all_dashboards, otherwise the save won't apply the changes
        dashboards = get_all_dashboards()
        key = (owner, dashboard_name)
        if key not in dashboards:
            raise MKUserError(
                "dashboard",
                _("The dashboard '%s' does not exist or you do not have permission to view it.")
                % dashboard_name,
            )

        return dashboards[key]

    def _get_view_spec(
        self,
        dashboard: DashboardConfig,
        embedded_id: str,
        mode: Mode,
    ) -> ViewSpec:
        view_name = f"{dashboard['name']}_{embedded_id}"
        if mode == "copy":
            view_spec = self._get_original_view_spec_from_request().copy()
            view_spec["name"] = view_name
            return view_spec

        if mode == "edit":
            return EmbeddedViewSpecManager.get_embedded_view_spec(dashboard, embedded_id, view_name)

        # create mode
        datasource = self._get_datasource_from_request()
        single_infos = self._get_single_infos_from_request()
        return self._create_new_view_spec(
            dashboard, embedded_id, view_name, datasource, single_infos
        )

    @staticmethod
    def _create_new_view_spec(
        dashboard: DashboardConfig,
        embedded_id: str,
        view_name: str,
        datasource: str,
        single_infos: SingleInfos,
    ) -> ViewSpec:
        embedded_views = dashboard.get("embedded_views", {})
        if embedded_id in embedded_views:
            raise MKUserError(
                "embedded_id",
                _(
                    "The dashboard '%s' already contains an embedded view with the ID '%s'. "
                    "Please choose another ID."
                )
                % (dashboard["name"], embedded_id),
            )

        return ViewSpec(
            owner=user.ident,
            name=view_name,
            single_infos=single_infos,
            datasource=datasource,
            layout="table",
            group_painters=[],
            painters=[],
            sorters=[],
            browser_reload=0,
            num_columns=1,
            column_headers="off",
            context={},
            add_context_to_title=False,
            title="",
            description="",
            topic="",
            sort_index=0,
            is_show_more=False,
            icon=None,
            hidden=False,
            hidebutton=False,
            public=False,
            packaged=False,
            link_from={},
            main_menu_search_terms=[],
        )
