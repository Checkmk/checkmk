#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.forms as forms
import cmk.gui.visuals as visuals
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu
from cmk.gui.plugins.views.utils import data_source_registry
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri
from cmk.gui.valuespec import DropdownChoice


def DatasourceSelection() -> DropdownChoice:
    """Create datasource selection valuespec, also for other modules"""
    return DropdownChoice(
        title=_("Datasource"),
        help=_("The datasources define which type of objects should be displayed with this view."),
        choices=data_source_registry.data_source_choices(),
        default_value="services",
    )


def page_create_view():
    show_create_view_dialog()


def show_create_view_dialog(next_url=None):
    vs_ds = DatasourceSelection()

    ds = "services"  # Default selection

    title = _("Create view")
    breadcrumb = visuals.visual_page_breadcrumb("views", title, "create")
    make_header(
        html,
        title,
        breadcrumb,
        make_simple_form_page_menu(
            _("View"),
            breadcrumb,
            form_name="create_view",
            button_name="_save",
            save_title=_("Continue"),
        ),
    )

    if request.var("_save") and transactions.check_transaction():
        try:
            ds = vs_ds.from_html_vars("ds")
            vs_ds.validate_value(ds, "ds")

            if not next_url:
                next_url = makeuri(
                    request,
                    [("datasource", ds)],
                    filename="create_view_infos.py",
                )
            else:
                next_url = next_url + "&datasource=%s" % ds
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("create_view")
    html.hidden_field("mode", "create")

    forms.header(_("Select Datasource"))
    forms.section(vs_ds.title())
    vs_ds.render_input("ds", ds)
    html.help(vs_ds.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()
