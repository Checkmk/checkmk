#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.crash_reporting import ABCCrashReport, CrashReportRegistry, CrashReportStore
from cmk.utils.site import omd_site

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, get_current_language
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.utils import escaping
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri, requested_file_name


def register(crash_report_registry: CrashReportRegistry) -> None:
    crash_report_registry.register(GUICrashReport)


class GUICrashReport(ABCCrashReport):
    @classmethod
    def type(cls):
        return "gui"

    @classmethod
    def from_exception(cls, details=None, type_specific_attributes=None):
        return super().from_exception(
            details={
                "page": requested_file_name(request) + ".py",
                "vars": {
                    key: "***" if value in ["password", "_password"] else value
                    for key, value in request.itervars()
                },
                "username": user.id,
                "user_agent": request.user_agent.string,
                "referer": request.referer,
                "is_mobile": is_mobile(request, response),
                "is_ssl_request": request.is_ssl_request,
                "language": get_current_language(),
                "request_method": request.request_method,
            },
        )

    def url(self) -> str:
        return makeuri(
            request,
            [
                ("site", omd_site()),
                ("crash_id", self.ident_to_text()),
            ],
            filename="crash.py",
        )


def handle_exception_as_gui_crash_report(
    details: dict | None = None,
    plain_error: bool = False,
    fail_silently: bool = False,
    show_crash_link: bool | None = None,
) -> GUICrashReport:
    crash = GUICrashReport.from_exception(details=details)
    CrashReportStore().save(crash)

    logger.exception("Unhandled exception (Crash ID: %s)", crash.ident_to_text())
    _show_crash_dump_message(crash, plain_error, fail_silently, show_crash_link)
    return crash


def _show_crash_dump_message(
    crash: "GUICrashReport", plain_text: bool, fail_silently: bool, show_crash_link: bool | None
) -> None:
    """Create a crash dump from a GUI exception and display a message to the user"""

    if show_crash_link is None:
        show_crash_link = user.may("general.see_crash_reports")

    title = _("Internal error")
    message = crash_dump_message(crash, show_crash_link)
    if plain_text:
        response.set_content_type("text/plain")
        response.set_data("%s\n" % escaping.strip_tags(message))
        return

    if fail_silently:
        return

    make_header(html, title, Breadcrumb())
    html.show_error(message)
    html.footer()


def crash_dump_message(crash: GUICrashReport, show_crash_link: bool) -> str:
    message = "%s: %s<br>\n<br>\n" % (_("Internal error"), crash.crash_info["exc_value"])

    # Do not reveal crash context information to unauthenticated users or not permitted
    # users to prevent disclosure of internal information
    if not show_crash_link:
        message += (
            _(
                "An internal error occurred while processing your request (Crash ID: %s). "
                "You can report this issue to your Checkmk administrator. "
                "Detailed information can be found on the crash report page "
                "or in <tt>var/log/web.log</tt>."
            )
            % crash.ident_to_text()
        )
    else:
        message += _(
            "An internal error occurred while processing your request (Crash ID: %s). "
            "You can report this issue to the Checkmk team to help "
            'fixing this issue. Please open the <a href="%s">crash report page</a> '
            "and use the form for reporting the problem."
        ) % (crash.ident_to_text(), crash.url())

    return message
