#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.visuals as visuals
from cmk.gui import forms
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.pages import Page, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.dashboard.utils import (
    DashboardConfig,
    dashlet_registry,
    dashlet_vs_general_settings,
    DashletConfig,
    DashletHandleInputFunc,
    DashletInputFunc,
    get_permitted_dashboards,
    save_all_dashboards,
)
from cmk.gui.plugins.visuals.utils import visual_info_registry
from cmk.gui.type_defs import SingleInfos
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import Dictionary, Transform, ValueSpec

__all__ = ["EditDashletPage"]


class EditDashletPage(Page):
    def __init__(self) -> None:
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to edit dashboards."))

        self._board = request.get_str_input_mandatory("name")
        self._ident = request.get_integer_input("id")

        try:
            self._dashboard = get_permitted_dashboards()[self._board]
        except KeyError:
            raise MKUserError("name", _("The requested dashboard does not exist."))

    def page(self) -> PageResult:  # pylint: disable=useless-return,too-many-branches
        if self._ident is None:
            type_name = request.get_str_input_mandatory("type")
            mode = "add"

            try:
                dashlet_type = dashlet_registry[type_name]
            except KeyError:
                raise MKUserError("type", _("The requested element type does not exist."))

            title = _("Add element: %s") % dashlet_type.title()

            # Initial configuration
            dashlet_spec: DashletConfig = {
                "position": dashlet_type.initial_position(),
                "size": dashlet_type.initial_size(),
                "single_infos": dashlet_type.single_infos(),
                "type": type_name,
            }
            dashlet_spec.update(dashlet_type.default_settings())

            if dashlet_type.has_context():
                dashlet_spec["context"] = {}

            self._ident = len(self._dashboard["dashlets"])

            single_infos_raw = request.var("single_infos")
            single_infos: SingleInfos = []
            if single_infos_raw:
                single_infos = single_infos_raw.split(",")
                for key in single_infos:
                    if key not in visual_info_registry:
                        raise MKUserError("single_infos", _("The info %s does not exist.") % key)

            if not single_infos:
                single_infos = dashlet_type.single_infos()

            dashlet_spec["single_infos"] = single_infos
        else:
            mode = "edit"

            try:
                dashlet_spec = self._dashboard["dashlets"][self._ident]
            except IndexError:
                raise MKUserError("id", _("The element does not exist."))

            type_name = dashlet_spec["type"]
            dashlet_type = dashlet_registry[type_name]
            single_infos = dashlet_spec["single_infos"]

            title = _("Edit element: %s") % dashlet_type.title()

        breadcrumb = dashlet_editor_breadcrumb(self._board, self._dashboard, title)
        make_header(
            html,
            title,
            breadcrumb=breadcrumb,
            page_menu=_dashlet_editor_page_menu(breadcrumb),
        )

        vs_general = dashlet_vs_general_settings(dashlet_type, single_infos)

        def dashlet_info_handler(dashlet_spec: DashletConfig) -> SingleInfos:
            assert isinstance(self._ident, int)
            dashlet_type = dashlet_registry[dashlet_spec["type"]]
            dashlet = dashlet_type(self._board, self._dashboard, self._ident, dashlet_spec)
            return dashlet.infos()

        context_specs = visuals.get_context_specs(
            dashlet_spec["single_infos"], dashlet_info_handler(dashlet_spec)
        )

        vs_type: ValueSpec | None = None
        params = dashlet_type.vs_parameters()
        render_input_func: DashletInputFunc | None = None
        handle_input_func: DashletHandleInputFunc | None = None
        if isinstance(params, list):
            # TODO: Refactor all params to be a Dictionary() and remove this special case
            vs_type = Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=dashlet_type.opt_parameters(),
                validate=dashlet_type.validate_parameters_func(),
                elements=params,
            )

        elif isinstance(params, (Dictionary, Transform)):
            vs_type = params

        elif isinstance(params, tuple):
            # It's a tuple of functions which should be used to render and parse the params
            render_input_func, handle_input_func = params

        # Check disjoint option on known valuespecs
        if isinstance(vs_type, Dictionary):
            settings_elements = {el[0] for el in vs_general._get_elements()}
            properties_elements = {el[0] for el in vs_type._get_elements()}
            assert settings_elements.isdisjoint(
                properties_elements
            ), "Dashboard element settings and properties have a shared option name"

        if request.var("_save") and transactions.transaction_valid():
            try:
                # Take over keys not managed by the edit dialog
                new_dashlet_spec = DashletConfig(
                    {
                        "type": dashlet_spec["type"],
                        "size": dashlet_spec["size"],
                        "position": dashlet_spec["position"],
                    }
                )

                general_properties = vs_general.from_html_vars("general")
                vs_general.validate_value(general_properties, "general")
                # We have to trust from_html_vars and validate_value for now
                new_dashlet_spec.update(general_properties)  # type: ignore[typeddict-item]

                if context_specs:
                    new_dashlet_spec["context"] = visuals.process_context_specs(context_specs)

                if vs_type:
                    type_properties = vs_type.from_html_vars("type")
                    vs_type.validate_value(type_properties, "type")
                    # We have to trust from_html_vars and validate_value for now
                    new_dashlet_spec.update(type_properties)  # type: ignore[typeddict-item]

                elif handle_input_func:
                    # The returned dashlet must be equal to the parameter! It is not replaced/re-added
                    # to the dashboard object. FIXME TODO: Clean this up!
                    # We have to trust from_html_vars and validate_value for now
                    new_dashlet_spec = handle_input_func(
                        self._ident, dashlet_spec, new_dashlet_spec
                    )

                if mode == "add":
                    self._dashboard["dashlets"].append(new_dashlet_spec)
                else:
                    self._dashboard["dashlets"][self._ident] = new_dashlet_spec

                save_all_dashboards()
                html.footer()
                raise HTTPRedirect(request.get_url_input("next", request.get_url_input("back")))

            except MKUserError as e:
                html.user_error(e)

        html.begin_form("dashlet", method="POST")
        vs_general.render_input("general", dict(dashlet_spec))
        if context_specs:
            visuals.render_context_specs(dashlet_spec["context"], context_specs)

        if vs_type:
            vs_type.render_input("type", dict(dashlet_spec))
        elif render_input_func:
            render_input_func(dashlet_spec)

        forms.end()
        html.show_localization_hint()
        html.hidden_fields()
        html.end_form()

        html.footer()
        return None


def _dashlet_editor_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(
        _("Element"), breadcrumb, form_name="dashlet", button_name="_save"
    )


def dashlet_editor_breadcrumb(name: str, board: DashboardConfig, title: str) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        mega_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic(board["topic"]).title(),
    )
    breadcrumb.append(
        BreadcrumbItem(
            visuals.visual_title("dashboard", board, {}),
            request.get_url_input("back"),
        )
    )

    breadcrumb.append(make_current_page_breadcrumb_item(title))

    return breadcrumb
