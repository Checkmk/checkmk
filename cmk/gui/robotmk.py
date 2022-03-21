#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re

from livestatus import LivestatusRow, lqencode, MKLivestatusNotFoundError, SiteId

from cmk.utils.type_defs import HostName, Tuple

import cmk.gui.pages
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import make_service_breadcrumb
from cmk.gui.sites import live, only_sites
from cmk.gui.utils.urls import makeuri_contextless


@cmk.gui.pages.register("robotmk")
def robotmk_page() -> cmk.gui.pages.PageResult:
    """Renders an iframe to view the content of the robotmk log file"""
    site_id, host_name, service_description = _get_mandatory_request_vars()

    breadcrumb: Breadcrumb = make_service_breadcrumb(HostName(host_name), service_description)
    html.header(
        _("Robotmk report of service %s on host %s") % (service_description, host_name),
        breadcrumb=breadcrumb,
    )

    try:
        content = _get_html_from_livestatus(host_name, service_description, site_id)
    except MKLivestatusNotFoundError:
        html.user_error(MKUserError(None, _("You are not permitted to view this page")))
        return

    if not content[0]:
        html.user_error(MKUserError(None, _("No logs could be found.")))
        return

    iframe: str = "robotmk"
    html.iframe(
        content="",
        src=makeuri_contextless(
            request,
            [
                ("site", site_id),
                ("host", host_name),
                ("service", service_description),
            ],
            filename="robotmk_report.py",
        ),
        name="robotmk_report",
        id_=iframe,
    )

    html.javascript('cmk.utils.content_scrollbar("main_page_content");')
    html.javascript(
        "cmk.utils.add_height_to_simple_bar_content_of_iframe(%s);" % json.dumps(iframe)
    )


@cmk.gui.pages.register("robotmk_report")
def robotmk_report_page() -> cmk.gui.pages.PageResult:
    """Renders the content of the robotmk html log file"""
    site_id, host_name, service_description = _get_mandatory_request_vars()

    content = _get_html_from_livestatus(host_name, service_description, site_id)

    html_content = _get_cleaned_html_content(content[0].decode("utf-8"))
    html.write_html(html_content)


def _get_mandatory_request_vars() -> Tuple[SiteId, HostName, str]:
    site_id: SiteId = SiteId(request.get_str_input_mandatory("site"))
    host_name: HostName = request.get_str_input_mandatory("host")
    service_description: str = request.get_str_input_mandatory("service")

    return site_id, host_name, service_description


def _get_cleaned_html_content(content: str) -> HTML:
    """HTML ships with links that will break our layout. Make them unusable"""
    cleaned_content = re.sub(
        '(href=("\\${relativeSource}"|"#\\${id}"))|(<a class="link".*</a>$)|(onclick="makeElementVisible\\(.*\\)")',
        "",
        content,
        flags=re.MULTILINE,
    )

    return HTML(cleaned_content)


def _get_html_from_livestatus(
    host_name: HostName, service_description: str, site_id: SiteId
) -> LivestatusRow:
    query = (
        "GET services\nColumns: robotmk_last_log\nFilter: host_name = %s\nFilter: service_description = %s\n"
        % (lqencode(host_name), lqencode(service_description))
    )

    with only_sites(site_id):
        row = live().query_row(query)

    return row
