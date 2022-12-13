#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Pages to create either linked_view or view dashlets"""

from typing import Callable

from cmk.utils.type_defs import UserId

import cmk.gui.visuals as visuals
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.plugins.dashboard.utils import (
    copy_view_into_dashlet,
    DashboardName,
    dashlet_registry,
    DashletConfig,
    DashletId,
    get_permitted_dashboards,
    LinkedViewDashletConfig,
    ViewDashletConfig,
)
from cmk.gui.type_defs import ViewName
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.views.data_source import data_source_registry
from cmk.gui.views.datasource_selection import show_create_view_dialog
from cmk.gui.views.page_edit_view import view_choices

from .page_edit_dashlet import dashlet_editor_breadcrumb
from .store import add_dashlet

__all__ = ["page_create_link_view_dashlet", "page_create_view_dashlet"]


def page_create_link_view_dashlet() -> None:
    """Choose an existing view from the list of available views"""
    name = request.get_str_input_mandatory("name")
    choose_view(name, _("Embed existing view"), _create_linked_view_dashlet_spec)


def _create_linked_view_dashlet_spec(dashlet_id: int, view_name: str) -> LinkedViewDashletConfig:
    return LinkedViewDashletConfig(
        {
            "type": "linked_view",
            "position": dashlet_registry["linked_view"].initial_position(),
            "size": dashlet_registry["linked_view"].initial_size(),
            "show_title": True,
            "name": view_name,
        }
    )


def page_create_view_dashlet() -> None:
    create = request.var("create", "1") == "1"
    name = request.get_str_input_mandatory("name")

    if create:
        url = makeuri(
            request,
            [("back", makeuri(request, []))],
            filename="create_view_dashlet_infos.py",
        )
        show_create_view_dialog(next_url=url)

    else:
        # Choose an existing view from the list of available views
        choose_view(name, _("Copy existing view"), _create_cloned_view_dashlet_spec)


def _create_cloned_view_dashlet_spec(dashlet_id: int, view_name: str) -> ViewDashletConfig:
    dashlet_spec = ViewDashletConfig(
        {
            "type": "view",
            "datasource": "hosts",
            "description": "",
            "position": dashlet_registry["linked_view"].initial_position(),
            "size": dashlet_registry["linked_view"].initial_size(),
            "hidden": False,
            "public": True,
            "show_title": True,
            "layout": "table",
            "browser_reload": 30,
            "num_columns": 1,
            "column_headers": "pergroup",
            "name": "",
            "owner": UserId.builtin(),
            "hidebutton": False,
            "group_painters": [],
            "painters": [],
            "sorters": [],
            "topic": "",
            "link_from": {},
            "icon": None,
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        }
    )

    # save the original context and override the context provided by the view
    copy_view_into_dashlet(dashlet_spec, dashlet_id, view_name)
    return dashlet_spec


def page_create_view_dashlet_infos() -> None:
    ds_name = request.get_str_input_mandatory("datasource")
    if ds_name not in data_source_registry:
        raise MKUserError("datasource", _("The given datasource is not supported"))

    # Create a new view by choosing the datasource and the single object types
    visuals.page_create_visual(
        "views",
        data_source_registry[ds_name]().infos,
        next_url=makeuri_contextless(
            request,
            [
                ("name", request.var("name")),
                ("type", "view"),
                ("datasource", ds_name),
                ("back", makeuri(request, [])),
                (
                    "next",
                    makeuri_contextless(
                        request,
                        [("name", request.var("name")), ("edit", "1")],
                        "dashboard.py",
                    ),
                ),
            ],
            filename="edit_dashlet.py",
        ),
    )


def choose_view(
    name: DashboardName,
    title: str,
    create_dashlet_spec_func: Callable[[DashletId, ViewName], DashletConfig],
) -> None:
    vs_view = DropdownChoice[str](
        title=_("View name"),
        choices=lambda: view_choices(allow_empty=False),
        sorted=True,
        no_preselect_title="",
    )

    try:
        dashboard = get_permitted_dashboards()[name]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    breadcrumb = dashlet_editor_breadcrumb(name, dashboard, title)
    make_header(
        html,
        title,
        breadcrumb=breadcrumb,
        page_menu=_choose_view_page_menu(breadcrumb),
    )

    if request.var("_save") and transactions.check_transaction():
        try:
            view_name = vs_view.from_html_vars("view")
            vs_view.validate_value(view_name, "view")
            assert view_name is not None

            dashlet_id = len(dashboard["dashlets"])
            dashlet_spec = create_dashlet_spec_func(dashlet_id, view_name)
            add_dashlet(dashlet_spec, dashboard)

            raise HTTPRedirect(
                makeuri_contextless(
                    request,
                    [
                        ("name", name),
                        ("id", str(dashlet_id)),
                        ("back", request.get_url_input("back")),
                    ],
                    filename="edit_dashlet.py",
                )
            )
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("choose_view")
    forms.header(_("Select view"))
    forms.section(vs_view.title())
    vs_view.render_input("view", None)
    html.help(vs_view.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()


def _choose_view_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(
        _("View"),
        breadcrumb,
        form_name="choose_view",
        button_name="_save",
        save_title=_("Continue"),
    )
