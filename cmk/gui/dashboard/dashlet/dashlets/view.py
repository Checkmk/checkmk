#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"

import copy
from typing import cast, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.dashboard.dashlet.base import IFrameDashlet
from cmk.gui.dashboard.type_defs import (
    ABCViewDashletConfig,
    DashletSize,
    EmbeddedViewDashletConfig,
    LinkedViewDashletConfig,
    ViewDashletConfig,
)
from cmk.gui.data_source import data_source_registry
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.type_defs import (
    HTTPVariables,
    SingleInfos,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.urls import makeuri_contextless, requested_file_name
from cmk.gui.views.store import get_all_views, get_permitted_views

VT = TypeVar("VT", bound=ABCViewDashletConfig)


def copy_view_into_dashlet(
    request: Request,
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

    def infos(self) -> SingleInfos:
        try:
            return self._get_infos_from_view_spec(self._get_view_spec())
        except MKUserError:
            # If the linked view does not exist anymore, we cannot determine infos for it
            # which can potentially crash the entire dashboard instead of just this dashlet
            return []
