#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, NotRequired, override, Self, TypedDict

import cmk.ccc.version as cmk_version
from cmk.ccc.crash_reporting import (
    ABCCrashReport,
    CrashReportRegistry,
    CrashReportStore,
    VersionInfo,
)
from cmk.ccc.site import omd_site

import cmk.utils.paths

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


class DashletDetails(TypedDict):
    dashlet_id: NotRequired[int]
    dashlet_type: NotRequired[str]
    dashlet_spec: NotRequired[dict[str, Any]]


class RequestDetails(TypedDict):
    page: str
    vars: dict[str, str]
    username: str | None
    user_agent: str
    referer: str | None
    is_mobile: bool
    is_ssl_request: bool
    language: str
    request_method: str


class GUIDetails(RequestDetails, DashletDetails):
    pass


class GUICrashReport(ABCCrashReport[GUIDetails]):
    @override
    @classmethod
    def type(cls) -> str:
        return "gui"

    @classmethod
    def from_exception(
        cls,
        crashdir: Path,
        version_info: VersionInfo,
        details: GUIDetails | None = None,
    ) -> Self:
        try:
            # Access any attribute to trigger proxy object lookup
            _x = request.meta
            request_details = RequestDetails(
                page=requested_file_name(request) + ".py",
                vars={
                    key: "***" if value in ["password", "_password"] else value
                    for key, value in request.itervars()
                },
                username=user.id,
                user_agent=request.user_agent.string,
                referer=request.referer,
                is_mobile=is_mobile(request, response),
                is_ssl_request=request.is_ssl_request,
                language=get_current_language(),
                request_method=request.request_method,
            )
        except (RuntimeError, AttributeError):
            # TODO: for the moment we set the request details to unknown, but we should probably
            #  introduce a new crash report type which does not require request details
            request_details = RequestDetails(
                page="unknown",
                vars={},
                username=None,
                user_agent="unknown",
                referer="unknown",
                is_mobile=False,
                is_ssl_request=False,
                language="unknown",
                request_method="unknown",
            )

        return cls(
            crashdir,
            cls.make_crash_info(version_info, GUIDetails(**{**(details or {}), **request_details})),  # type: ignore[typeddict-item]
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
    details: GUIDetails | None = None,
    plain_error: bool = False,
    fail_silently: bool = False,
    show_crash_link: bool | None = None,
) -> GUICrashReport:
    crash = create_gui_crash_report(details)
    logger.exception("Unhandled exception (Crash ID: %s)", crash.ident_to_text())
    _show_crash_dump_message(crash, plain_error, fail_silently, show_crash_link)
    return crash


def create_gui_crash_report(
    details: GUIDetails | None = None,
) -> GUICrashReport:
    crash = GUICrashReport.from_exception(
        cmk.utils.paths.crash_dir,
        cmk_version.get_general_version_infos(cmk.utils.paths.omd_root),
        details=details,
    )
    CrashReportStore().save(crash)
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
    message = "{}: {}<br>\n<br>\n".format(_("Internal error"), crash.crash_info["exc_value"])

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
