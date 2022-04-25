#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
import re
import tarfile
import time
from typing import Literal

from livestatus import LivestatusRow, lqencode, MKLivestatusNotFoundError, SiteId

from cmk.utils.type_defs import HostName, Tuple

import cmk.gui.pages
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.plugins.views.utils import make_service_breadcrumb
from cmk.gui.sites import live, only_sites
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode


@cmk.gui.pages.page_registry.register_page("robotmk")
class ModeRobotmkPage(cmk.gui.pages.Page):
    @classmethod
    def ident(cls) -> str:
        return "robotmk"

    def _title(self) -> str:
        return _("Robot Framework: %s") % (
            _("Last log") if self._is_last_log() else _("Last error log")
        )

    def _report_type(self) -> str:
        return request.get_str_input_mandatory("report_type")

    def page(self) -> cmk.gui.pages.PageResult:
        """Renders an iframe to view the content of the RobotMK log file"""
        site_id, host_name, service_description = _get_mandatory_request_vars()

        breadcrumb: Breadcrumb = make_service_breadcrumb(HostName(host_name), service_description)
        title = self._title() + _(" of service %s on host %s") % (service_description, host_name)
        try:
            content = _get_html_from_livestatus(
                self._report_type(), site_id, host_name, service_description
            )
        except MKLivestatusNotFoundError:
            html.header(
                title=title,
                breadcrumb=breadcrumb,
            )
            html.user_error(MKUserError(None, _("You are not permitted to view this page")))
            return

        if not content[0]:
            html.header(
                title=title,
                breadcrumb=breadcrumb,
            )
            html.user_error(MKUserError(None, _("No logs could be found.")))
            return

        # Only render page menu with download option if content is not empty
        # and user is permitted
        html.header(
            title=title,
            breadcrumb=breadcrumb,
            page_menu=self._page_menu(breadcrumb, site_id, host_name, service_description),
        )

        iframe: str = self._report_type()
        html.iframe(
            content="",
            src=makeuri_contextless(
                request,
                [
                    ("report_type", self._report_type()),
                    ("site", site_id),
                    ("host", host_name),
                    ("service", service_description),
                ],
                filename="robotmk_report.py",
            ),
            name="%s_report" % self._report_type(),
            id_=iframe,
        )

        html.javascript('cmk.utils.content_scrollbar("main_page_content");')
        html.javascript(
            "cmk.utils.add_height_to_simple_bar_content_of_iframe(%s);" % json.dumps(iframe)
        )

    def _is_last_log(self) -> bool:
        return self._report_type() == "robotmk"

    def _page_menu(
        self,
        breadcrumb: Breadcrumb,
        site_id: SiteId,
        host_name: HostName,
        service_description: str,
    ) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="robotmk_logs",
                    title=_("RobotMK logs"),
                    topics=[
                        PageMenuTopic(
                            title=_("This log"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Download"),
                                    icon_name="download",
                                    item=make_simple_link(
                                        makeuri(
                                            request,
                                            [
                                                ("report_type", self._report_type()),
                                                ("site", site_id),
                                                ("host", host_name),
                                                ("service", service_description),
                                            ],
                                            filename="download_robotmk_report.py",
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Other logs for this service"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Last error log")
                                    if self._is_last_log()
                                    else _("Last log"),
                                    icon_name="robotmk_error" if self._is_last_log() else "robotmk",
                                    item=make_simple_link(
                                        makeuri(
                                            request,
                                            [
                                                (
                                                    "report_type",
                                                    "robotmk_error"
                                                    if self._is_last_log()
                                                    else "robotmk",
                                                ),
                                                ("site", site_id),
                                                ("host", host_name),
                                                ("service", service_description),
                                            ],
                                            filename="robotmk.py",
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )


@cmk.gui.pages.register("robotmk_report")
def robotmk_report_page() -> cmk.gui.pages.PageResult:
    """Renders the content of the RobotMK html log file"""
    site_id, host_name, service_description = _get_mandatory_request_vars()
    report_type: str = request.get_str_input_mandatory("report_type")

    content = _get_html_from_livestatus(report_type, site_id, host_name, service_description)

    html_content = _get_cleaned_html_content(content[0].decode("utf-8"))
    html.write_html(html_content)


@cmk.gui.pages.register("download_robotmk_report")
def robotmk_download_page() -> cmk.gui.pages.PageResult:
    user.need_permission("general.see_crash_reports")

    site_id, host_name, service_description = _get_mandatory_request_vars()
    report_type: str = request.get_str_input_mandatory("report_type")

    filename = "Robot_Framework_log_%s_%s_%s_%s.tar.gz" % (
        urlencode(site_id),
        urlencode(host_name),
        urlencode(service_description),
        time.strftime("%Y-%m-%d_%H-%M-%S"),
    )

    response.headers["Content-Disposition"] = "Attachment; filename=%s" % filename
    response.headers["Content-Type"] = "application/x-tar"
    html_content: bytes = _get_html_from_livestatus(
        report_type, site_id, host_name, service_description
    )[0]
    response.set_data(_pack_html_content(report_type, html_content))


def _pack_html_content(name: str, html_content: bytes) -> bytes:
    """Returns a byte string representing the current robotmk report in tar archive format"""
    buf = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        tar_info = tarfile.TarInfo(name="%s_log.html" % name)
        tar_info.size = len(html_content)

        tar.addfile(tar_info, io.BytesIO(html_content))

    return buf.getvalue()


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
    report_type: str,
    site_id: SiteId,
    host_name: HostName,
    service_description: str,
) -> LivestatusRow:

    report_column: Literal["robotmk_last_log", "robotmk_last_error_log"] = (
        "robotmk_last_log" if report_type == "robotmk" else "robotmk_last_error_log"
    )
    query = (
        "GET services\nColumns: %s\nFilter: host_name = %s\nFilter: service_description = %s\n"
        % (report_column, lqencode(host_name), lqencode(service_description))
    )

    with only_sites(site_id):
        row = live().query_row(query)

    return row
