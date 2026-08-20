#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, NotRequired, override, Self, TypedDict

import cmk.ccc.version_info as cmk_version_info
import cmk.utils.paths
from cmk.ccc.site import omd_site
from cmk.crash import (
    ABCCrashReport,
    CrashInfo,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, get_current_language
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.utils.mobile import is_mobile
from cmk.web.utils import escaping
from cmk.web.utils.urls import makeuri, makeuri_contextless, requested_file_name


class DashletDetails(TypedDict):
    dashlet_id: NotRequired[int]
    dashlet_type: NotRequired[str]
    dashlet_spec: NotRequired[Mapping[str, object]]


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
    @classmethod
    @override
    def type(cls) -> str:
        return "gui"

    @classmethod
    @override
    def make_crash_info(
        cls, version_info: VersionInfo, details: GUIDetails
    ) -> CrashInfo[GUIDetails]:
        crash_info = super().make_crash_info(version_info, details)
        crash_info["exc_value"] = escaping.strip_tags(crash_info["exc_value"])
        return crash_info

    @classmethod
    def from_exception(
        cls,
        *,
        version_info: VersionInfo,
        details: GUIDetails | None = None,
        crash_report_base_path: Path,
    ) -> Self:
        try:
            # Access any attribute to trigger proxy object lookup
            _x = request.meta
            request_details = RequestDetails(
                page=requested_file_name(request) + ".py",
                vars=dict(request.itervars()),
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

        if details is None:
            return cls(
                crash_report_base_path=crash_report_base_path,
                crash_info=cls.make_crash_info(
                    version_info,
                    GUIDetails(
                        page=request_details["page"],
                        vars=request_details["vars"],
                        username=request_details["username"],
                        user_agent=request_details["user_agent"],
                        referer=request_details["referer"],
                        is_mobile=request_details["is_mobile"],
                        is_ssl_request=request_details["is_ssl_request"],
                        language=request_details["language"],
                        request_method=request_details["request_method"],
                    ),
                ),
            )
        return cls(
            crash_report_base_path=crash_report_base_path,
            crash_info=cls.make_crash_info(
                version_info,
                GUIDetails(**{**details, **request_details}),
            ),
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


class JavascriptDetails(TypedDict):
    url: str
    component: str
    user_agent: str
    username: str | None
    language: str
    context: str


class JavascriptCrashReport(ABCCrashReport[JavascriptDetails]):
    """Crash report for an error caught in the browser by the Checkmk frontend.

    Unlike the other crash types the exception did not happen in this process, so
    the exception fields are filled from the data the browser reported instead of
    from the current Python exception context.
    """

    _V8_FRAME: Final = re.compile(r"^at\s+(?:(?P<function>.*?)\s+)?\((?P<location>.+)\)$")
    _V8_BARE_FRAME: Final = re.compile(r"^at\s+(?P<location>[^\s()]+)$")
    _SPIDERMONKEY_FRAME: Final = re.compile(r"^(?P<function>[^@]*)@(?P<location>.+)$")
    _FRAME_LOCATION: Final = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?::\d+)?$")

    @classmethod
    @override
    def type(cls) -> str:
        return "javascript"

    @classmethod
    def from_browser_error(
        cls,
        *,
        version_info: VersionInfo,
        error_name: str,
        error_message: str,
        stack: str,
        details: JavascriptDetails,
        crash_report_base_path: Path,
    ) -> Self:
        crash_info = cls.make_crash_info(version_info, details)
        crash_info["exc_type"] = escaping.strip_tags(error_name)
        crash_info["exc_value"] = escaping.strip_tags(error_message)
        crash_info["exc_traceback"] = cls.parse_stack(stack)
        crash_info["local_vars"] = ""
        return cls(crash_report_base_path=crash_report_base_path, crash_info=crash_info)

    def url(self) -> str:
        return makeuri_contextless(
            request,
            [
                ("site", str(omd_site())),
                ("crash_id", self.ident_to_text()),
            ],
            filename="crash.py",
        )

    @classmethod
    def parse_stack(cls, stack: str) -> Sequence[tuple[str, int, str, str]]:
        """Turn a browser stack trace into the frame format used by all crash reports.

        Frames the browser reported without a source location, and the leading
        ``Name: message`` line V8 prepends, have no frame representation and are
        dropped.
        """
        return [
            frame
            for line in stack.splitlines()
            if (frame := cls._parse_frame(line.strip())) is not None
        ]

    @classmethod
    def _parse_frame(cls, line: str) -> tuple[str, int, str, str] | None:
        for pattern in (cls._V8_FRAME, cls._V8_BARE_FRAME, cls._SPIDERMONKEY_FRAME):
            if (frame := pattern.match(line)) is None:
                continue
            if (location := cls._FRAME_LOCATION.match(frame["location"])) is None:
                continue
            function = (frame.groupdict().get("function") or "").strip()
            return (
                location["file"],
                int(location["line"]),
                function or "<anonymous>",
                line,
            )
        return None


def handle_exception_as_gui_crash_report(
    details: GUIDetails | None = None,
    plain_error: bool = False,
    fail_silently: bool = False,
    show_crash_link: bool | None = None,
    *,
    debug: bool,
    inject_js_profiling_code: bool,
    load_frontend_vue: str,
    custom_style_sheet: str | None,
    screenshotmode: bool,
) -> GUICrashReport:
    crash = create_gui_crash_report(details)
    logger.exception(
        "Unhandled exception (Crash ID: %(crash_id)s)", {"crash_id": crash.ident_to_text()}
    )
    _show_crash_dump_message(
        crash,
        plain_error,
        fail_silently,
        show_crash_link,
        debug=debug,
        inject_js_profiling_code=inject_js_profiling_code,
        load_frontend_vue=load_frontend_vue,
        custom_style_sheet=custom_style_sheet,
        screenshotmode=screenshotmode,
    )
    return crash


def create_gui_crash_report(
    details: GUIDetails | None = None,
) -> GUICrashReport:
    crash = GUICrashReport.from_exception(
        version_info=cmk_version_info.get_general_version_infos(cmk.utils.paths.omd_root),
        details=details,
        crash_report_base_path=make_crash_report_base_path(cmk.utils.paths.omd_root),
    )
    CrashReportStore().save(crash)
    return crash


def _show_crash_dump_message(
    crash: "GUICrashReport",
    plain_text: bool,
    fail_silently: bool,
    show_crash_link: bool | None,
    *,
    debug: bool,
    inject_js_profiling_code: bool,
    load_frontend_vue: str,
    custom_style_sheet: str | None,
    screenshotmode: bool,
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

    make_header(
        html,
        title=title,
        breadcrumb=Breadcrumb(),
        debug=debug,
        lang=user.language,
        inject_js_profiling_code=inject_js_profiling_code,
        load_frontend_vue=load_frontend_vue,
        custom_style_sheet=custom_style_sheet,
        screenshotmode=screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )
    html.show_error(message)
    html.footer()


def crash_dump_message(crash: GUICrashReport, show_crash_link: bool) -> str:
    message = "{}: {}<br>\n<br>\n".format(_("Internal error"), crash.crash_info["exc_value"])

    # Do not reveal crash context information to unauthenticated users or not permitted
    # users to prevent disclosure of internal information
    if not show_crash_link:
        message += _(
            "An internal error occurred while processing your request (crash ID: %(crash_id)s). "
            "You can report this issue to your Checkmk administrator. "
            "Detailed information can be found on the crash report page "
            "or in <tt>var/log/web.log</tt>."
        ) % {"crash_id": crash.ident_to_text()}
    else:
        message += _(
            "An internal error occurred while processing your request (crash ID: %(crash_id)s). "
            "You can report this issue to the Checkmk team to help "
            'fixing this issue. Please open the <a href="%(url)s">crash report page</a> '
            "and use the form for reporting the problem."
        ) % {"crash_id": crash.ident_to_text(), "url": crash.url()}

    return message
