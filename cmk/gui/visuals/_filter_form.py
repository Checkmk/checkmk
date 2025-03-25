#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping
from typing import Any

from cmk.gui import forms
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel

from ._filter_valuespecs import VisualFilterListWithAddPopup


def render_filter_form(
    info_list: SingleInfos, context: VisualContext, page_name: str, reset_ajax_page: str
) -> HTML:
    with output_funnel.plugged():
        show_filter_form(info_list, context, page_name, reset_ajax_page)
        return HTML.without_escaping(output_funnel.drain())


def show_filter_form(
    info_list: SingleInfos, context: VisualContext, page_name: str, reset_ajax_page: str
) -> None:
    html.show_user_errors()
    form_name: str = "filter"
    with html.form_context(
        form_name,
        method="GET",
        add_transid=False,
        onsubmit=f"cmk.forms.on_filter_form_submit_remove_vars({json.dumps('form_' + form_name)});",
    ):
        varprefix = ""
        vs_filters = VisualFilterListWithAddPopup(info_list=info_list)

        filter_list_id = VisualFilterListWithAddPopup.filter_list_id(varprefix)
        filter_list_selected_id = filter_list_id + "_selected"
        _show_filter_form_buttons(
            varprefix,
            filter_list_id,
            vs_filters._page_request_vars,
            page_name,
            reset_ajax_page,
            context,
        )

        html.open_div(id_=filter_list_selected_id, class_=["side_popup_content"])
        vs_filters.render_input(varprefix, context)
        html.close_div()

        forms.end()

        html.hidden_fields()
    html.javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_selected_id))

    # The filter popup is shown automatically when it has been submitted before on page reload. To
    # know that the user closed the popup after filtering, we have to hook into the close_popup
    # function.
    html.final_javascript(
        "cmk.page_menu.register_on_open_handler('popup_filters', cmk.page_menu.on_filter_popup_open);"
        "cmk.page_menu.register_on_close_handler('popup_filters', cmk.page_menu.on_filter_popup_close);"
        f"cmk.forms.add_filter_form_error_listener('{filter_list_selected_id}');"
    )


def _show_filter_form_buttons(
    varprefix: str,
    filter_list_id: str,
    page_request_vars: Mapping[str, Any] | None,
    view_name: str,
    reset_ajax_page: str,
    context: VisualContext,
) -> None:
    html.open_div(class_="side_popup_controls")

    html.open_a(
        href="javascript:void(0);",
        onclick="cmk.page_menu.toggle_popup_filter_list(this, %s)" % json.dumps(filter_list_id),
        class_="add",
    )
    html.icon("add")
    html.div(_("Add filter"), class_="description")
    html.close_a()

    html.open_div(class_="update_buttons")
    html.button("%s_apply" % varprefix, _("Apply filters"), cssclass="apply hot")
    html.jsbutton(
        "%s_reset" % varprefix,
        _("Reset"),
        cssclass="reset",
        onclick="cmk.valuespecs.visual_filter_list_reset(%s, %s, %s, %s, %s)"
        % (
            json.dumps(varprefix),
            json.dumps(page_request_vars),
            json.dumps(view_name),
            json.dumps(reset_ajax_page),
            json.dumps(context),
        ),
    )
    html.close_div()
    html.close_div()
