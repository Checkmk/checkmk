#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import base64
import io
import json
import pprint
import tarfile
import time
import traceback
from typing import Dict, Iterator, Mapping, Optional, Type, TypedDict

import livestatus
from livestatus import SiteId

import cmk.utils.crash_reporting
import cmk.utils.version as cmk_version
from cmk.utils.crash_reporting import CrashInfo

import cmk.gui.forms as forms
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.userdb as userdb
import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config, html, request, response, user_errors
from cmk.gui.htmllib import HTML, HTMLContent
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.views.crash_reporting import CrashReportsRowTable
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode, urlencode_vars
from cmk.gui.valuespec import Dictionary, EmailAddress, TextInput


class ReportSubmitDetails(TypedDict):
    name: str
    mail: str


class ABCCrashReportPage(cmk.gui.pages.Page, abc.ABC):
    def __init__(self):
        super().__init__()
        self._crash_id = request.get_str_input_mandatory("crash_id")
        self._site_id = request.get_str_input_mandatory("site")

    def _get_crash_info(self, row) -> CrashInfo:
        return json.loads(row["crash_info"])

    def _get_crash_row(self):
        row = self._get_crash_report_row(self._crash_id, self._site_id)
        if not row:
            raise MKUserError(
                None,
                _(
                    "Could not find the requested crash %s on site %s. "
                    "Maybe the automatic cleanup found more than 200 crash reports "
                    "below ~/var/check_mk/crashes and already deleted the requested crash report."
                )
                % (self._crash_id, self._site_id),
            )
        return row

    def _get_crash_report_row(self, crash_id: str, site_id: str) -> Optional[Dict[str, str]]:
        rows = CrashReportsRowTable().get_crash_report_rows(
            only_sites=[SiteId(site_id)],
            filter_headers="Filter: id = %s" % livestatus.lqencode(crash_id),
        )
        if not rows:
            return None
        return rows[0]

    def _get_serialized_crash_report(self):
        return {
            k: v
            for k, v in self._get_crash_row().items()
            if k not in ["site", "crash_id", "crash_type"]
        }


@cmk.gui.pages.page_registry.register_page("crash")
class PageCrash(ABCCrashReportPage):
    def page(self) -> None:
        row = self._get_crash_row()
        crash_info = self._get_crash_info(row)

        title = _("Crash report: %s") % self._crash_id
        breadcrumb = self._breadcrumb(title)
        html.header(title, breadcrumb, self._page_menu(breadcrumb, crash_info))

        # Do not reveal crash context information to unauthenticated users or not permitted
        # users to prevent disclosure of internal information
        if not user.may("general.see_crash_reports"):
            html.show_error("<b>%s:</b> %s" % (_("Internal error"), crash_info["exc_value"]))
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

        if request.has_var("_report") and transactions.check_transaction():
            details = self._handle_report_form(crash_info)
        else:
            details = ReportSubmitDetails(name="", mail="")

        if crash_info["crash_type"] == "gui":
            html.show_error("<b>%s:</b> %s" % (_("Internal error"), crash_info["exc_value"]))
            html.p(
                _(
                    "An internal error occured while processing your request. "
                    "You can report this issue to the Checkmk team to help "
                    "fixing this issue. Please use the form below for reporting."
                )
            )

        self._warn_about_local_files(crash_info)
        self._show_report_form(crash_info, details)
        self._show_crash_report(crash_info)
        self._show_crash_report_details(crash_info, row)

        html.footer()

    def _breadcrumb(self, title: str) -> Breadcrumb:
        breadcrumb = make_topic_breadcrumb(
            mega_menu_registry.menu_monitoring(), PagetypeTopics.get_topic("analyze")
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

    def _page_menu(self, breadcrumb: Breadcrumb, crash_info: CrashInfo) -> PageMenu:
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
                                    icon_name="download",
                                    item=make_simple_link(
                                        makeuri(request, [], filename="download_crash_report.py")
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
                            entries=list(self._page_menu_entries_related_monitoring(crash_info)),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo
    ) -> Iterator[PageMenuEntry]:
        renderer = self._crash_type_renderer(crash_info["crash_type"])
        yield from renderer.page_menu_entries_related_monitoring(crash_info, self._site_id)

    def _handle_report_form(self, crash_info: CrashInfo) -> ReportSubmitDetails:
        details: ReportSubmitDetails
        try:
            vs = self._vs_crash_report()
            details = vs.from_html_vars("_report")
            vs.validate_value(details, "_report")

            # Make the resulting page execute the crash report post request
            url_encoded_params = urlencode_vars(
                [
                    ("name", details["name"]),
                    ("mail", details["mail"]),
                    (
                        "crashdump",
                        base64.b64encode(
                            _pack_crash_report(self._get_serialized_crash_report())
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
                filename="mailto:" + self._get_crash_report_target(),
            )
            html.show_error(
                _(
                    "Failed to send the crash report. Please download it manually and send it "
                    'to <a href="%s">%s</a>'
                )
                % (report_url, self._get_crash_report_target())
            )
            html.close_div()
            html.javascript(
                "cmk.transfer.submit_crash_report(%s, %s);"
                % (json.dumps(config.crash_report_url), json.dumps(url_encoded_params))
            )
        except MKUserError as e:
            user_errors.add(e)

        return details

    def _get_version(self) -> str:
        return cmk_version.__version__

    def _get_crash_report_target(self) -> str:
        return config.crash_report_target

    def _vs_crash_report(self):
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
                        title=_("Email Address"),
                        allow_empty=False,
                    ),
                ),
            ],
            optional_keys=[],
            render="form",
        )

    def _warn_about_local_files(self, crash_info: CrashInfo) -> None:
        if crash_info["crash_type"] == "check":
            files = []
            for filepath, _lineno, _func, _line in crash_info["exc_traceback"]:
                if "/local/" in filepath:
                    files.append(filepath)

            if files:
                warn_text = escaping.escape_to_html(
                    _(
                        "The following files located in the local hierarchy of your site are involved in this exception:"
                    )
                )
                warn_text += html.render_ul(HTML("\n").join(map(html.render_li, files)))
                warn_text += escaping.escape_to_html(
                    _(
                        "Maybe these files are not compatible with your current Checkmk "
                        "version. Please verify and only report this crash when you think "
                        "this should be working."
                    )
                )
                html.show_warning(warn_text)

    def _show_report_form(self, crash_info: CrashInfo, details: ReportSubmitDetails) -> None:
        if crash_info["crash_type"] == "gui":
            self._add_gui_user_infos_to_details(details)

        html.begin_form("report", method="GET")
        html.show_user_errors()
        vs = self._vs_crash_report()
        vs.render_input("_report", details)
        vs.set_focus("report")
        forms.end()
        html.button("_report", _("Submit Report"))
        html.hidden_fields()
        html.end_form()

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
            _("Exception"), "%s (%s)" % (info["exc_type"], info["exc_value"]), odd=True, pre=True
        )
        _crash_row(
            _("Traceback"), self._format_traceback(info["exc_traceback"]), odd=False, pre=True
        )
        _crash_row(
            _("Local Variables"),
            format_local_vars(info["local_vars"]) if "local_vars" in info else "",
            odd=True,
            pre=True,
        )

        _crash_row(_("Crash Type"), info["crash_type"], odd=False, legend=True)
        _crash_row(
            _("Time"), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["time"])), odd=True
        )
        _crash_row(_("Operating System"), info["os"], False)
        _crash_row(_("Checkmk Version"), info["version"], True)
        _crash_row(_("Edition"), info.get("edition", ""), False)
        _crash_row(_("Core"), info.get("core", ""), True)
        _crash_row(_("Python Version"), info.get("python_version", _("Unknown")), False)

        joined_paths = html.render_br().join(info.get("python_paths", [_("Unknown")]))
        _crash_row(_("Python Module Paths"), joined_paths, odd=False)

        html.close_table()

    def _format_traceback(self, tb):
        return "".join(traceback.format_list(tb))

    def _show_crash_report_details(self, crash_info: CrashInfo, row):
        self._crash_type_renderer(crash_info["crash_type"]).show_details(crash_info, row)

    def _crash_type_renderer(self, crash_type):
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
    def show_details(self, crash_info: CrashInfo, row):
        raise NotImplementedError()


class ReportRendererRegistry(cmk.utils.plugin_registry.Registry[Type[ABCReportRenderer]]):
    def plugin_name(self, instance):
        return instance.type()


report_renderer_registry = ReportRendererRegistry()


@report_renderer_registry.register
class ReportRendererGeneric(ABCReportRenderer):
    @classmethod
    def type(cls):
        return "generic"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        # We don't want to produce anything here
        yield from ()

    def show_details(self, crash_info: CrashInfo, row) -> None:
        if not crash_info["details"]:
            return

        html.h3(_("Details"), class_="table")
        html.p(
            _("No detail renderer for crash of type '%s' available. Details structure is:")
            % crash_info["crash_type"]
        )
        html.pre(pprint.pformat(crash_info["details"]))


@report_renderer_registry.register
class ReportRendererSection(ABCReportRenderer):
    @classmethod
    def type(cls):
        return "section"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        # We don't want to produce anything here
        yield from ()

    def show_details(self, crash_info: CrashInfo, row) -> None:
        self._show_crashed_section_details(crash_info)
        self._show_section_content(row)

    def _show_crashed_section_details(self, info: CrashInfo) -> None:
        def format_bool(val):
            return {
                True: _("Yes"),
                False: _("No"),
                None: _("Unknown"),
            }[val]

        details = info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_="data")

        _crash_row(_("Section Name"), details["section_name"], odd=True)
        _crash_row(_("Inline-SNMP"), format_bool(details.get("inline_snmp")), odd=False, pre=True)

        html.close_table()

    def _show_section_content(self, row) -> None:
        _crash_row(_("Section Content"), repr(row.get("section_content")))


@report_renderer_registry.register
class ReportRendererCheck(ABCReportRenderer):
    @classmethod
    def type(cls):
        return "check"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        host = crash_info["details"]["host"]
        service = crash_info["details"]["description"]

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
            title=_("Host status"),
            icon_name="status",
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
            title=_("Service status"),
            icon_name="status",
            item=make_simple_link(service_url),
        )

    def show_details(self, crash_info: CrashInfo, row) -> None:
        self._show_crashed_check_details(crash_info)
        self._show_agent_output(row)

    def _show_crashed_check_details(self, info: CrashInfo) -> None:
        def format_bool(val):
            return {
                True: _("Yes"),
                False: _("No"),
                None: _("Unknown"),
            }[val]

        details = info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_="data")

        _crash_row(_("Host"), details["host"], odd=False, legend=True)
        _crash_row(_("Is Cluster Host"), format_bool(details.get("is_cluster")), odd=True)
        _crash_row(_("Check Type"), details["check_type"], odd=False)
        _crash_row(_("Manual Check"), format_bool(details.get("manual_check")), odd=True, pre=True)
        _crash_row(_("Inline-SNMP"), format_bool(details.get("inline_snmp")), odd=True, pre=True)
        _crash_row(_("Check Item"), details.get("item", "This check has no item."), odd=False)
        _crash_row(_("Description"), details["description"], odd=True)
        if "params" in details:
            _crash_row(_("Parameters"), format_params(details["params"]), odd=False, pre=True)
        else:
            _crash_row(_("Parameters"), "This Check has no parameters", odd=False)

        html.close_table()

    def _show_agent_output(self, row):
        agent_output = row.get("agent_output")
        if agent_output:
            assert isinstance(agent_output, bytes)
            _show_output_box(_("Agent output"), agent_output)


@report_renderer_registry.register
class ReportRendererGUI(ABCReportRenderer):
    @classmethod
    def type(cls):
        return "gui"

    def page_menu_entries_related_monitoring(
        self, crash_info: CrashInfo, site_id: SiteId
    ) -> Iterator[PageMenuEntry]:
        # We don't want to produce anything here
        return
        yield  # pylint: disable=unreachable

    def show_details(self, crash_info: CrashInfo, row) -> None:
        details = crash_info["details"]

        html.h3(_("Details"), class_="table")
        html.open_table(class_="data")

        _crash_row(_("Page"), details["page"], odd=False, legend=True)
        _crash_row(_("Request Method"), details.get("request_method", _("Unknown")))
        html.open_tr(class_="data even0")
        html.td(_("HTTP Parameters"), class_="left")
        html.open_td()
        html.debug_vars(vars_=details["vars"], hide_with_mouse=False)
        html.close_td()
        html.close_tr()
        _crash_row(_("Referer"), details.get("referer", _("Unknown")))
        _crash_row(_("Username"), details["username"], odd=False)
        _crash_row(_("User Agent"), details["user_agent"])
        _crash_row(_("Mobile GUI"), details["is_mobile"], odd=False)
        _crash_row(_("SSL"), details["is_ssl_request"])
        _crash_row(_("Language"), details["language"], odd=False)

        html.close_table()


def _crash_row(
    title: str, infotext: HTMLContent, odd: bool = True, legend: bool = False, pre: bool = False
) -> None:
    trclass = "data odd0" if odd else "data even0"
    tdclass = "left legend" if legend else "left"
    html.open_tr(class_=trclass)
    html.td(title, class_=tdclass)
    if pre:
        html.td(html.render_pre(infotext))
    else:
        html.td(infotext)
    html.close_tr()


# Local vars are a base64 encoded repr of the python dict containing the local vars of
# the exception context. Decode it!
def format_local_vars(local_vars):
    return base64.b64decode(local_vars).decode()


def format_params(params):
    return pprint.pformat(params)


def _show_output_box(title: str, content: bytes) -> None:
    html.h3(title, class_="table")
    html.open_div(class_="log_output")
    html.write_html(
        HTML(
            escaping.escape_attribute(content.decode(errors="surrogateescape"))
            .replace("\n", "<br>")
            .replace(" ", "&nbsp;")
        )
    )
    html.close_div()


@cmk.gui.pages.page_registry.register_page("download_crash_report")
class PageDownloadCrashReport(ABCCrashReportPage):
    def page(self):
        user.need_permission("general.see_crash_reports")

        filename = "Checkmk_Crash_%s_%s_%s.tar.gz" % (
            urlencode(self._site_id),
            urlencode(self._crash_id),
            time.strftime("%Y-%m-%d_%H-%M-%S"),
        )

        response.headers["Content-Disposition"] = "Attachment; filename=%s" % filename
        response.headers["Content-Type"] = "application/x-tar"
        response.set_data(_pack_crash_report(self._get_serialized_crash_report()))


def _pack_crash_report(serialized_crash_report: Mapping[str, Optional[bytes]]) -> bytes:
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
