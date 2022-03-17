#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from pathlib import Path

import cmk.utils.store as store
from cmk.utils import paths
from cmk.utils.type_defs import HostName

import cmk.gui.pages
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import make_service_breadcrumb
from cmk.gui.utils.urls import makeuri_contextless


@cmk.gui.pages.register("robotmk")
def robotmk_page() -> cmk.gui.pages.PageResult:
    """Renders an iframe to view the content of the robotmk log file"""
    site_id: str = request.get_str_input_mandatory("site")
    host_name: HostName = request.get_str_input_mandatory("host")
    service_description: str = request.get_str_input_mandatory("service")

    breadcrumb: Breadcrumb = make_service_breadcrumb(HostName(host_name), service_description)
    html.header(
        _("Robotmk report of service %s on host %s") % (service_description, host_name),
        breadcrumb=breadcrumb,
    )

    last_log_path: str = "/%s/%s/suite_last_log.html" % (host_name, service_description)

    robotmk_logfile_path: Path = Path(str(paths.robotmk_html_log_dir) + last_log_path)
    if not robotmk_logfile_path.exists():
        html.user_error(
            MKUserError(None, _("Report file %s could not be found.") % robotmk_logfile_path)
        )
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
                ("path", str(robotmk_logfile_path)),
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
    robotmk_logfile_path: str = request.get_str_input_mandatory("path")

    content: str = store.load_text_from_file(Path(robotmk_logfile_path))
    if content is None:
        return

    html.write_html(HTML(_get_cleaned_content(content)))


def _get_cleaned_content(content: str) -> str:
    """HTML ships with links that will break our layout. Make them unusable"""
    cleaned_content = re.sub(
        '(href=("\\${relativeSource}"|"#\\${id}"))|(<a class="link".*</a>$)|(onclick="makeElementVisible\\(.*\\)")',
        "",
        content,
        flags=re.MULTILINE,
    )

    return cleaned_content
