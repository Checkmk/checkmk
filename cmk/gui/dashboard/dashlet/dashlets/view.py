#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Sequence
from typing import cast, Literal

from cmk.utils.type_defs import UserId

from cmk.gui import visuals
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import (
    HTTPVariables,
    Icon,
    LinkFromSpec,
    PainterSpec,
    SorterSpec,
    VisualContext,
)
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.views.store import get_all_views, get_permitted_views

from ..base import DashletConfig


class ABCViewDashletConfig(DashletConfig):
    name: str


class LinkedViewDashletConfig(ABCViewDashletConfig):
    ...


class _ViewDashletConfigMandatory(ABCViewDashletConfig):
    # TODO: Find a way to clean up the rendundancies with ViewSpec and Visual
    # From: Visual
    owner: UserId
    # These fields are redundant between DashletConfig and Visual
    # name: str
    # context: VisualContext
    # single_infos: SingleInfos
    # title: str | LazyString
    add_context_to_title: bool
    description: str | LazyString
    topic: str
    sort_index: int
    is_show_more: bool
    icon: Icon | None
    hidden: bool
    hidebutton: bool
    public: bool | tuple[Literal["contact_groups"], Sequence[str]]
    # From: ViewSpec
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: list[PainterSpec]
    painters: list[PainterSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup", "repeat"]
    sorters: Sequence[SorterSpec]


class ViewDashletConfig(_ViewDashletConfigMandatory, total=False):
    # TODO: Find a way to clean up the rendundancies with ViewSpec and Visual
    # From: Visual
    link_from: LinkFromSpec
    # From: ViewSpec
    add_headers: str
    # View editor only adds them in case they are truish. In our builtin specs these flags are also
    # partially set in case they are falsy
    mobile: bool
    mustsearch: bool
    force_checkboxes: bool
    user_sortable: bool
    play_sounds: bool


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
                    "Failed to convert a builtin dashboard which is referencing "
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
    dashlet["title_url"] = makeuri_contextless(
        request,
        name_part + singlecontext_vars,
        filename="view.py",
    )

    dashlet["type"] = "view"
    dashlet["name"] = "dashlet_%d" % nr
    dashlet["show_title"] = True
    dashlet["mustsearch"] = False
