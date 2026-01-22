#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import abc
import base64
import dataclasses
import io
import json
import pprint
import tarfile
import time
import traceback
from collections.abc import Iterator, Mapping, Sequence
from typing import cast, override, Protocol, Self, TypedDict

import livestatus

import cmk.ccc.version as cmk_version
from cmk.ccc.crash_reporting import CrashInfo, SENSITIVE_KEYWORDS
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.gui import forms, userdb
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.debug_vars import debug_vars
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.http import ContentDispositionType, Request, request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode, urlencode_vars
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Dictionary, EmailAddress, TextInput

from .helpers import local_files_involved_in_crash
from .views import CrashReportsRowTable

CrashReportRow = dict[str, str]


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("crash", PageCrash()))
    page_registry.register(PageEndpoint("download_crash_report", PageDownloadCrashReport()))
    report_renderer_registry.register(ReportRendererGeneric)
    report_renderer_registry.register(ReportRendererSection)
    report_renderer_registry.register(ReportRendererCheck)
    report_renderer_registry.register(ReportRendererGUI)


class ReportSubmitDetails(TypedDict):
    name: str
    mail: str


class CrashReportsRowFetcher(Protocol):
    def get_crash_report_rows(
        self, only_sites: livestatus.OnlySites, filter_headers: str
    ) -> Iterator[dict[str, str]]: ...


@dataclasses.dataclass(frozen=True)
class CrashReport:
    crash_id: str
    site_id: str
    row: CrashReportRow
    info: CrashInfo

    @classmethod
    def build(cls, request: Request, fetcher: CrashReportsRowFetcher) -> Self:
        return cls(
            crash_id=(crash_id := request.get_str_input_mandatory("crash_id")),
            site_id=(site_id := request.get_str_input_mandatory("site")),
            row=(row := cls._extract_row(fetcher, crash_id, site_id)),
            info=json.loads(row["crash_info"]),
        )

    @staticmethod
    def _extract_row(
        fetcher: CrashReportsRowFetcher, crash_id: str, site_id: str
    ) -> CrashReportRow:
        try:
            return next(
                fetcher.get_crash_report_rows(
                    only_sites=[SiteId(site_id)],
                    filter_headers="Filter: id = %s" % livestatus.lqencode(crash_id),
                )
            )
        except StopIteration:
            raise MKUserError(
                None,
                _(
                    "Could not find the requested crash %s on site %s. "
                    "Maybe the automatic cleanup found more than 200 crash reports "
                    "below ~/var/check_mk/crashes and already deleted the requested crash report."
                )
                % (crash_id, site_id),
            )


def _get_serialized_crash_report(row: CrashReportRow) -> Mapping[str, bytes | None]:
    return {k: v.encode() for k, v in row.items() if k not in ["site", "crash_id", "crash_type"]}


class PageCrash(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        report = CrashReport.build(ctx.request, CrashReportsRowTable())
        title = _("Crash report: %s") % report.crash_id

        permissions = UserPermissions.from_config(ctx.config, permission_registry)
        breadcrumb = self._breadcrumb(ctx.request, title, permissions)

        page_menu = self._page_menu(ctx.request, breadcrumb, report.info, report.site_id)
        make_header(html, title, breadcrumb, page_menu)

        # Do not reveal crash context information to unauthenticated users or not permitted
        # users to prevent disclosure of internal information
        if not user.may("general.see_crash_reports"):
            html.p(
                _(
                    "An internal error occurred while processing your request. "
                    "You can report this issue to your Checkmk administrator. "
                    "Detailed information can be found on the crash report page "
                    "or in <tt>var/log/web.log</tt>."
                )
            )
            html.footer()
            return

        if ctx.request.has_var("_report") and transactions.check_transaction():
            details = self._handle_report_form(
                ctx.request, ctx.config.crash_report_target, ctx.config.crash_report_url, report.row
            )
        else:
            details = ReportSubmitDetails(name="", mail="")

        html.show_warning(
            _(
                "Crash reports might contain sensitive information such as secrets. "
                "It is advised that you manually review the content of this report and "
                "ensure any additional sensitive data is removed before sharing the crash report."
            )
        )

        if report.info["crash_type"] == "gui":
            html.show_error("<b>{}:</b> {}".format(_("Internal error"), report.info["exc_value"]))
            html.p(
                _(
                    "An internal error occurred while processing your request. "
                    "You can report this issue to the Checkmk team to help "
                    "fixing this issue. Please use the form below for reporting."
                )
            )

        self._warn_about_sensitive_information(report.info)
        self._warn_about_local_files(report.info)
        self._show_report_form(report.info, details)
        self._show_crash_report(report.info)
        self._show_crash_report_details(report.info, report.row)

        html.footer()

    def _breadcrumb(
        self, request: Request, title: str, user_permissions: UserPermissions
    ) -> Breadcrumb:
        breadcrumb = make_topic_breadcrumb(
            main_menu_registry.menu_monitoring(),
            PagetypeTopics.get_topic("analyze", user_permissions).title(),
        )

        # Add the parent element: List of all crashes
        breadcrumb.append(
            BreadcrumbItem(
                title=_("Crash reports"),
                url=makeuri_contextless(
                    request,
                    [("view_name", "crash_reports")],
                    filename="view.py",
                ),
            )
        )

        breadcrumb.append(make_current_page_breadcrumb_item(title))

        return breadcrumb

    def _page_menu(
        self, request: Request, breadcrumb: Breadcrumb, info: CrashInfo, site_id: str
    ) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="crash_reports",
                    title=_("Crash reports"),
                    topics=[
                        PageMenuTopic(
                            title=_("This crash report"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Download"),
                                    icon_name=StaticIcon(IconNames.download),
                                    item=make_simple_link(
                                        makeuri(
                                            request,
                                            [],
                                            filename="download_crash_report.py",
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Monitoring"),
                            entries=list(self._page_menu_entries_related_monitoring(info, site_id)),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_related_monitoring(
        self, info: CrashInfo, site_id: str
    ) -> Iterator[PageMenuEntry]:
        renderer = self._crash_type_renderer(info["crash_type"])
        yield from renderer.page_menu_entries_related_monitoring(info, SiteId(site_id))

    def _handle_report_form(
        self,
        request: Request,
        crash_report_target: str,
        crash_report_url: str,
        row: CrashReportRow,
    ) -> ReportSubmitDetails:
        details = ReportSubmitDetails(name="", mail="")
        try:
            vs = self._vs_crash_report()
            raw_details = vs.from_html_vars("_report")
            vs.validate_value(raw_details, "_report")
            details = cast(ReportSubmitDetails, raw_details)

            # Make the resulting page execute the crash report post request
            url_encoded_params = urlencode_vars(
                [
                    ("name", details["name"]),
                    ("mail", details["mail"]),
                    (
                        "crashdump",
                        base64.b64encode(
                            _pack_crash_report(_get_serialized_crash_report(row))
                        ).decode("ascii"),
                    ),
                ]
            )
            html.open_div(id_="pending_msg", style="display:none")
            html.show_message(_("Submitting crash report..."))
            html.close_div()
            html.open_div(id_="success_msg", style="display:none")
            html.show_message(
                _(
                    "Your crash report has been submitted (ID: ###ID###). Thanks for your participation, "
                    "it is very important for the quality of Checkmk.<br><br>"
                    "Please note:"
                    "<ul>"
                    "<li>In general we do <i>not</i> respond to crash reports, "
                    "except we need further information from you.</li>"
                    "<li>We read every feedback thoroughly, but this might happen "
                    "not before a couple of weeks or even months have passed and is "
                    "often aligned with our release cycle.</li>"
                    "<li>If you are in need of a quick solution for your problem, then "
                    "we can help you within the scope of professional support. If you "
                    "already have a support contract, then please use your personal "
                    "support email address to send us a mail refering to your crash "
                    "report.<br>If you are interested in the details about support, "
                    'you find details on <a href="https://checkmk.com/'
                    'checkmk_support_contract.html" target="_blank">our website</a>.'
                )
            )
            html.close_div()
            html.open_div(id_="fail_msg", style="display:none")
            report_url = makeuri_contextless(
                request,
                [
                    ("subject", "Checkmk Crash Report - " + self._get_version()),
                ],
                filename="mailto:" + crash_report_target,
            )
            html.show_error(
                _(
                    "Failed to send the crash report. Please download it manually and send it "
                    'to <a href="%s">%s</a> or try again later.'
                )
                % (report_url, crash_report_target)
            )
            html.close_div()
            html.javascript(
                f"cmk.transfer.submit_crash_report({json.dumps(crash_report_url)}, {json.dumps(url_encoded_params)});"
            )
        except MKUserError as e:
            user_errors.add(e)

        return details

    def _get_version(self) -> str:
        return cmk_version.__version__

    def _vs_crash_report(self) -> Dictionary:
        return Dictionary(
            title=_("Crash Report"),
            elements=[
                (
                    "name",
                    TextInput(
                        title=_("Name"),
                        allow_empty=False,
                    ),
                ),
                (
                    "mail",
                    EmailAddress(
                        title=_("Email address"),
                        allow_empty=False,
                    ),
                ),
            ],
            optional_keys=[],
            render="form",
        )

    def _warn_about_local_files(self, crash_info: CrashInfo) -> None:
        files = local_files_involved_in_crash(crash_info["exc_traceback"])
        if not files:
            return

        warn_text = HTML.with_escaping(
            _(
                "The following files located in the local hierarchy of your site are involved in this exception:"
            )
        )
        warn_text += HTMLWriter.render_ul(
            HTML.without_escaping("\n").join(map(HTMLWriter.render_li, files))
        )
        warn_text += HTML.with_escaping(
            _(
                "Maybe these files are not compatible with your current Checkmk "
                "version. Please verify and only report this crash when you think "
                "this should be working."
            )
        )
        html.show_warning(warn_text)

    def _warn_about_sensitive_information(self, crash_info: CrashInfo) -> None:
        if not ((vars_ := crash_info.get("details") or {}).get("vars")):
            return

        if any(
            sensitive_keyword in key.lower()
            for sensitive_keyword in SENSITIVE_KEYWORDS
            for key in vars_
        ):
            html.show_warning(
                _(
                    "Checkmk has identified and attempted to redact sensitive information in the crash report."
                )
            )

    def _show_report_form(self, crash_info: CrashInfo, details: ReportSubmitDetails) -> None:
        if crash_info["crash_type"] == "gui":
            self._add_gui_user_infos_to_details(details)

        with html.form_context("report", method="GET"):
            html.show_user_errors()
            vs = self._vs_crash_report()
            vs.render_input("_report", dict(details))
            vs.set_focus("report")
            forms.end()
            html.button("_report", _("Submit report"), cssclass="hot")
            html.hidden_fields()

    def _add_gui_user_infos_to_details(self, details: ReportSubmitDetails) -> None:
        users = userdb.load_users()
        if user.id is None:
            details.update({"name": "", "mail": ""})
            return
        user_spec = users.get(user.id, {})
        details.setdefault("name", user_spec.get("alias", ""))
        details.setdefault("mail", user_spec.get("mail", ""))

    def _show_crash_report(self, info: CrashInfo) -> None:
        html.h3(_("Crash Report"), class_="table")
        html.open_table(class_=["data", "crash_report"])

        _crash_row(
            _("Exception"),
            "{} ({})".format(info["exc_type"], info["exc_value"]),
            odd=True,
            pre=True,
        )
        _crash_row(
            _("Traceback"),
            "".join(
                [
                    self._format_traceback(info["exc_traceback"]),
                    info["exc_value"],
                ]
            ),
            odd=False,
            pre=True,
        )
        _crash_row(
            _("Local Variables"),
            format_local_vars(info["local_vars"]) if "local_vars" in info else "",
            odd=True,
            pre=True,
        )

        _crash_row(_("Crash Type"), info["crash_type"], odd=False, legend=True)
        _crash_row(
            _("Time"),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(info["time"]))),
            odd=True,
        )
        _crash_row(_("Operating System"), info["os"], False)
        _crash_row(_("Checkmk Version"), info["version"], True)
        _crash_row(_("Edition"), info.get("edition", ""), False)
        _crash_row(_("Core"), info.get("core", ""), True)
        _crash_row(_("Python Version"), info.get("python_version", _("Unknown")), False)

        joined_paths = HTMLWriter.render_br().join(info.get("python_paths", [_("Unknown")]))
        _crash_row(_("Python Module Paths"), joined_paths, odd=False)

        html.close_table()

    def _format_traceback(self, tb: Sequence[tuple[str, int, str, str]]) -> str:
        return "".join(traceback.format_list(tb))

    def _show_crash_report_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        self._crash_type_renderer(crash_info["crash_type"]).show_details(crash_info, row)

    def _crash_type_renderer(self, crash_type: str) -> ABCReportRenderer:
        return report_renderer_registry.get(crash_type, report_renderer_registry["generic"])()


class ABCReportRenderer(abc.ABC):
    """Render crash type individual GUI elements"""

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        raise NotImplementedError()

    @abc.abstractmethod
    def show_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        raise NotImplementedError()


class ReportRendererRegistry(Registry[type[ABCReportRenderer]]):
    def plugin_name(self, instance: type[ABCReportRenderer]) -> str:
        return instance.type()


report_renderer_registry = ReportRendererRegistry()


class ReportRendererGeneric(ABCReportRenderer):
    @classmethod
    def type(cls) -> str:
        return "generic"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        # We don't want to produce anything here
        yield from ()

    def show_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        if not crash_info["details"]:
            return

        html.h3(_("Details"), class_="table")
        html.p(
            _("No detail renderer for crash of type '%s' available. Details structure is:")
            % crash_info["crash_type"]
        )
        html.pre(pprint.pformat(crash_info["details"]))


class ReportRendererSection(ABCReportRenderer):
    @classmethod
    def type(cls) -> str:
        return "section"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        # We don't want to produce anything here
        yield from ()

    def show_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        self._show_crashed_section_details(crash_info)
        _show_agent_output(row)

    def _show_crashed_section_details(self, info: CrashInfo) -> None:
        def format_bool(val: bool | None) -> str:
            return {
                True: _("Yes"),
                False: _("No"),
                None: _("Unknown"),
            }[val]

        details = info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_=["data", "crash_report"])

        _crash_row(_("Section Name"), details["section_name"], odd=True)
        _crash_row(
            _("Inline SNMP"),
            format_bool(details.get("inline_snmp")),
            odd=False,
            pre=True,
        )
        _crash_row(
            _("Section Content"),
            pprint.pformat(details.get("section_content")),
            pre=True,
        )

        html.close_table()


class ReportRendererCheck(ABCReportRenderer):
    @classmethod
    def type(cls) -> str:
        return "check"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        details = crash_info["details"]
        host = details["host"]
        service = details["description"]

        host_url = makeuri(
            request,
            [
                ("view_name", "hoststatus"),
                ("host", host),
                ("site", site_id),
            ],
            filename="view.py",
        )
        yield PageMenuEntry(
            title=_("Host state"),
            icon_name=StaticIcon(IconNames.status),
            item=make_simple_link(host_url),
        )

        service_url = makeuri(
            request,
            [
                ("view_name", "service"),
                ("host", host),
                ("service", service),
                (
                    "site",
                    site_id,
                ),
            ],
            filename="view.py",
        )
        yield PageMenuEntry(
            title=_("Service state"),
            icon_name=StaticIcon(IconNames.status),
            item=make_simple_link(service_url),
        )

    def show_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        self._show_crashed_check_details(crash_info)
        _show_agent_output(row)

    def _show_crashed_check_details(self, info: CrashInfo) -> None:
        def format_bool(val: bool | None) -> str:
            return {
                True: _("Yes"),
                False: _("No"),
                None: _("Unknown"),
            }[val]

        details = info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_="data")

        _crash_row(_("Host"), details["host"], odd=False, legend=True)
        _crash_row(_("Is cluster host"), format_bool(details.get("is_cluster")), odd=True)
        _crash_row(_("Check type"), details["check_type"], odd=False)
        _crash_row(
            _("Enforced service"),
            format_bool(details.get("enforced_service")),
            odd=True,
            pre=True,
        )
        _crash_row(
            _("Inline SNMP"),
            format_bool(details.get("inline_snmp")),
            odd=True,
            pre=True,
        )
        _crash_row(_("Check item"), details.get("item", "This check has no item."), odd=False)
        _crash_row(_("Description"), details["description"], odd=True)
        if "params" in details:
            _crash_row(_("Parameters"), format_params(details["params"]), odd=False, pre=True)
        else:
            _crash_row(_("Parameters"), "This check has no parameters", odd=False)

        html.close_table()


class ReportRendererGUI(ABCReportRenderer):
    @classmethod
    def type(cls) -> str:
        return "gui"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        """Produces nothing"""
        yield from ()

    def show_details(self, crash_info: CrashInfo, row: CrashReportRow) -> None:
        details = crash_info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_="data")

        _crash_row(_("Page"), details["page"], odd=False, legend=True)
        _crash_row(_("Request method"), details.get("request_method", _("Unknown")))
        html.open_tr(class_="data even0")
        html.td(_("HTTP Parameters"), class_="left")
        html.open_td()
        debug_vars(html, request, vars_=details["vars"], hide_with_mouse=False)
        html.close_td()
        html.close_tr()
        _crash_row(_("Referer"), details.get("referer", _("Unknown")))
        _crash_row(_("Username"), details["username"], odd=False)
        _crash_row(_("User agent"), details["user_agent"])
        _crash_row(_("Mobile GUI"), details["is_mobile"], odd=False)
        _crash_row(_("SSL"), details["is_ssl_request"])
        _crash_row(_("Language"), details["language"], odd=False)

        html.close_table()


def _crash_row(
    title: str,
    infotext: HTMLContent,
    odd: bool = True,
    legend: bool = False,
    pre: bool = False,
) -> None:
    trclass = "data odd0" if odd else "data even0"
    tdclass = "left legend" if legend else "left"
    html.open_tr(class_=trclass)
    html.td(title, class_=tdclass)
    html.td(HTMLWriter.render_pre(infotext) if pre else infotext)
    html.close_tr()


# Local vars are a base64 encoded repr of the python dict containing the local vars of
# the exception context. Decode it!
def format_local_vars(local_vars: str) -> str:
    return base64.b64decode(local_vars).decode()


def format_params(params: object) -> str:
    return pprint.pformat(params)


def _show_output_box(title: str, content: bytes) -> None:
    html.h3(title, class_="table")
    html.open_div(class_="log_output")
    html.write_html(
        HTML.without_escaping(
            escaping.escape_attribute(content.decode(errors="surrogateescape"))
            .replace("\n", "<br>")
            .replace(" ", "&nbsp;")
        )
    )
    html.close_div()


def _show_agent_output(row: CrashReportRow) -> None:
    agent_output = row.get("agent_output")
    if agent_output:
        _show_output_box(_("Agent output"), agent_output.encode())


class PageDownloadCrashReport(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        user.need_permission("general.see_crash_reports")
        report = CrashReport.build(ctx.request, CrashReportsRowTable())

        filename = "Checkmk_Crash_{}_{}_{}.tar.gz".format(
            urlencode(report.site_id),
            urlencode(report.crash_id),
            time.strftime("%Y-%m-%d_%H-%M-%S"),
        )
        response.set_content_type("application/x-tgz")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, filename)
        response.set_data(_pack_crash_report(_get_serialized_crash_report(report.row)))


def _pack_crash_report(serialized_crash_report: Mapping[str, bytes | None]) -> bytes:
    """Returns a byte string representing the current crash report in tar archive format"""
    buf = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        for key, content in serialized_crash_report.items():
            if content is None:
                continue

            tar_info = tarfile.TarInfo(name="crash.info" if key == "crash_info" else key)
            tar_info.size = len(content)

            tar.addfile(tar_info, io.BytesIO(content))

    return buf.getvalue()
