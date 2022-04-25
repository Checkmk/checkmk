from typing import Dict, Optional

import cmk.utils.crash_reporting
from cmk.utils.site import omd_site

import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.context import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri, requested_file_name

CrashReportStore = cmk.utils.crash_reporting.CrashReportStore


@cmk.utils.crash_reporting.crash_report_registry.register
class GUICrashReport(cmk.utils.crash_reporting.ABCCrashReport):
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
                "language": cmk.gui.i18n.get_current_language(),
                "request_method": request.request_method,
            },
        )


def handle_exception_as_gui_crash_report(
    details: Optional[Dict] = None,
    plain_error: bool = False,
    fail_silently: bool = False,
    show_crash_link: Optional[bool] = None,
) -> None:
    crash = GUICrashReport.from_exception(details=details)
    CrashReportStore().save(crash)

    logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())
    _show_crash_dump_message(crash, plain_error, fail_silently, show_crash_link)


def _show_crash_dump_message(
    crash: "GUICrashReport", plain_text: bool, fail_silently: bool, show_crash_link: Optional[bool]
) -> None:
    """Create a crash dump from a GUI exception and display a message to the user"""

    if show_crash_link is None:
        show_crash_link = user.may("general.see_crash_reports")

    title = _("Internal error")
    message = "%s: %s<br>\n<br>\n" % (title, crash.crash_info["exc_value"])
    # Do not reveal crash context information to unauthenticated users or not permitted
    # users to prevent disclosure of internal information
    if not show_crash_link:
        message += _(
            "An internal error occurred while processing your request. "
            "You can report this issue to your Checkmk administrator. "
            "Detailed information can be found on the crash report page "
            "or in <tt>var/log/web.log</tt>."
        )
    else:
        crash_url = makeuri(
            request,
            [
                ("site", omd_site()),
                ("crash_id", crash.ident_to_text()),
            ],
            filename="crash.py",
        )
        message += (
            _(
                "An internal error occured while processing your request. "
                "You can report this issue to the Checkmk team to help "
                'fixing this issue. Please open the <a href="%s">crash report page</a> '
                "and use the form for reporting the problem."
            )
            % crash_url
        )

    if plain_text:
        response.set_content_type("text/plain")
        response.set_data("%s\n" % escaping.strip_tags(message))
        return

    if fail_silently:
        return

    html.header(title, Breadcrumb())
    html.show_error(message)
    html.footer()
