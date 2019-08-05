#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import base64
import tarfile
import StringIO
import time
import pprint
import traceback
import json
from typing import Dict, Text  # pylint: disable=unused-import
import six

import cmk.gui.pages
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.userdb as userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    EmailAddress,
    TextUnicode,
    Dictionary,
)
import cmk.gui.config as config
import cmk.gui.forms as forms
import cmk.utils.crash_reporting

CrashReportStore = cmk.utils.crash_reporting.CrashReportStore


def show_crash_dump_message(crash, plain_text, fail_silently):
    # type: (GUICrashReport, bool, bool) -> None
    """Create a crash dump from a GUI exception and display a message to the user"""

    title = _("Internal error")
    message = u"%s: %s<br>\n<br>\n" % (title, crash.crash_info["exc_value"])
    # Do not reveal crash context information to unauthenticated users or not permitted
    # users to prevent disclosure of internal information
    if not config.user.may("general.see_crash_reports"):
        message += _("An internal error occurred while processing your request. "
                     "You can report this issue to your Checkmk administrator. "
                     "Detailed information can be found on the crash report page "
                     "or in <tt>var/log/web.log</tt>.")
    else:
        crash_url = html.makeuri(
            [
                ("site", config.omd_site()),
                ("crash_id", crash.ident_to_text()),
            ],
            filename="crash.py",
        )
        message += _("An internal error occured while processing your request. "
                     "You can report this issue to the Checkmk team to help "
                     "fixing this issue. Please open the <a href=\"%s\">crash report page</a> "
                     "and use the form for reporting the problem.") % crash_url

    if plain_text:
        html.set_output_format("text")
        html.write("%s\n" % html.strip_tags(message))
        return

    if fail_silently:
        return

    html.header(title)
    html.show_error(message)
    html.footer()


@cmk.utils.crash_reporting.crash_report_registry.register
class GUICrashReport(cmk.utils.crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        return "gui"

    @classmethod
    def from_exception(cls, details=None, type_specific_attributes=None):
        return super(GUICrashReport, cls).from_exception(details={
            "page": html.myfile + ".py",
            "vars": {
                key: "***" if value in ["password", "_password"] else value
                for key, value in html.request.itervars()
            },
            "username": config.user.id,
            "user_agent": html.request.user_agent,
            "referer": html.request.referer,
            "is_mobile": html.is_mobile(),
            "is_ssl_request": html.request.is_ssl_request,
            "language": cmk.gui.i18n.get_current_language(),
            "request_method": html.request.request_method,
        },)


class ABCCrashReportPage(six.with_metaclass(abc.ABCMeta, cmk.gui.pages.Page)):
    def __init__(self):
        super(ABCCrashReportPage, self).__init__()
        self._crash_id = html.get_unicode_input("crash_id")
        if not self._crash_id:
            raise MKUserError("crash_id", _("The parameter \"%s\" is missing.") % "crash_id")

        self._site_id = html.get_unicode_input("site")
        if not self._site_id:
            raise MKUserError("site", _("The parameter \"%s\" is missing.") % "site")

    def _get_crash_info(self, row):
        return json.loads(row["crash_info"])

    def _get_crash_row(self):
        row = _get_crash_report_row(self._crash_id, self._site_id)
        if not row:
            raise MKUserError(
                None,
                _("Could not find the requested crash %s on site %s") %
                (self._crash_id, self._site_id))
        return row

    def _get_serialized_crash_report(self):
        return {k: v for k, v in self._get_crash_row().iteritems() if k not in ["site", "crash_id"]}


@cmk.gui.pages.page_registry.register_page("crash")
class PageCrash(ABCCrashReportPage):
    def page(self):
        html.header(_("Crash report: %s") % self._crash_id)
        row = self._get_crash_row()
        crash_info = self._get_crash_info(row)

        # Do not reveal crash context information to unauthenticated users or not permitted
        # users to prevent disclosure of internal information
        if not config.user.may("general.see_crash_reports"):
            html.header(_("Internal error"))
            html.show_error("<b>%s:</b> %s" % (_("Internal error"), crash_info["exc_value"]))
            html.p(
                _("An internal error occurred while processing your request. "
                  "You can report this issue to your Checkmk administrator. "
                  "Detailed information can be found on the crash report page "
                  "or in <tt>var/log/web.log</tt>."))
            html.footer()
            return

        self._show_context_buttons(crash_info)

        if html.request.has_var("_report") and html.check_transaction():
            details = self._handle_report_form(crash_info)
        else:
            details = {}

        if crash_info["crash_type"] == "gui":
            html.show_error("<b>%s:</b> %s" % (_("Internal error"), crash_info["exc_value"]))
            html.p(
                _("An internal error occured while processing your request. "
                  "You can report this issue to the Checkmk team to help "
                  "fixing this issue. Please use the form below for reporting."))

        self._warn_about_local_files(crash_info)
        self._show_report_form(crash_info, details)
        self._show_crash_report(crash_info)
        self._show_crash_report_details(crash_info, row)

        html.footer()

    def _show_context_buttons(self, crash_info):
        html.begin_context_buttons()

        html.context_button(_("All crashes"), "view.py?view_name=crash_reports", "crash")

        # TODO: Cleanup different handlings
        if crash_info["crash_type"] == "check":
            host = crash_info["host"]
            service = crash_info["description"]

            host_url = html.makeuri(
                [
                    ("view_name", "hoststatus"),
                    ("host", host),
                    ("site", self._site_id),
                ],
                filename="view.py",
            )
            html.context_button(_("Host status"), host_url, "status")

            service_url = html.makeuri(
                [("view_name", "service"), ("host", host), ("service", service),
                 (
                     "site",
                     self._site_id,
                 )],
                filename="view.py",
            )
            html.context_button(_("Service status"), service_url, "status")

        download_url = html.makeuri([], filename="download_crash_report.py")
        html.context_button(_("Download"), download_url, "download")

        html.end_context_buttons()

    def _handle_report_form(self, crash_info):
        details = {}
        try:
            vs = self._vs_crash_report()
            details = vs.from_html_vars("_report")
            vs.validate_value(details, "_report")

            # Make the resulting page execute the crash report post request
            url_encoded_params = html.urlencode_vars(details.items() + [
                ("crashdump",
                 base64.b64encode(_pack_crash_report(self._get_serialized_crash_report()))),
            ])
            html.open_div(id_="pending_msg", style="display:none")
            html.message(_("Submitting crash report..."))
            html.close_div()
            html.open_div(id_="success_msg", style="display:none")
            html.message(
                _("Your crash report has been submitted (ID: ###ID###). Thanks for your participation, "
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
                  "you find details on <a href=\"https://checkmk.com/"
                  "checkmk_support_contract.html\" target=_blank>our website</a>."))
            html.close_div()
            html.open_div(id_="fail_msg", style="display:none")
            report_url = html.makeuri([
                ("subject", "Checkmk Crash Report - " + self._get_version()),
            ],
                                      filename="mailto:" + self._get_crash_report_target())
            html.show_error(
                _("Failed to send the crash report. Please download it manually and send it "
                  "to <a href=\"%s\">%s</a>") % (report_url, self._get_crash_report_target()))
            html.close_div()
            html.javascript("cmk.crash_reporting.submit('https://crash.checkmk.com', " \
                                                "'%s');" % url_encoded_params)
        except MKUserError as e:
            action_message = "%s" % e
            html.add_user_error(e.varname, action_message)

        return details

    def _get_version(self):
        # type: () -> Text
        return cmk.__version__

    def _get_crash_report_target(self):
        # type: () -> Text
        return config.crash_report_target

    def _vs_crash_report(self):
        return Dictionary(
            title=_("Crash Report"),
            elements=[
                ("name", TextUnicode(
                    title=_("Name"),
                    allow_empty=False,
                )),
                ("mail", EmailAddress(
                    title=_("Email Address"),
                    allow_empty=False,
                )),
            ],
            optional_keys=[],
            render="form",
        )

    def _warn_about_local_files(self, crash_info):
        if crash_info["crash_type"] == "check":
            files = []
            for filepath, _lineno, _func, _line in crash_info["exc_traceback"]:
                if "/local/" in filepath:
                    files.append(filepath)

            if files:
                warn_text = _(
                    "The following files located in the local hierarchy of your site are involved in this exception:"
                )
                warn_text += html.render_ul(HTML("\n").join(map(html.render_li, files)))
                warn_text += _("Maybe these files are not compatible with your current Checkmk "
                               "version. Please verify and only report this crash when you think "
                               "this should be working.")
                html.show_warning(warn_text)

    def _show_report_form(self, crash_info, details):
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

    def _add_gui_user_infos_to_details(self, details):
        users = userdb.load_users()
        user = users.get(config.user.id, {})
        details.setdefault("name", user.get("alias"))
        details.setdefault("mail", user.get("mail"))

    def _show_crash_report(self, info):
        html.h2(_("Crash Report"))
        html.open_table(class_=["data", "crash_report"])

        _crash_row(_("Exception"),
                   "%s (%s)" % (info["exc_type"], info["exc_value"]),
                   odd=True,
                   pre=True)
        _crash_row(_("Traceback"),
                   self._format_traceback(info["exc_traceback"]),
                   odd=False,
                   pre=True)
        _crash_row(_("Local Variables"),
                   format_local_vars(info["local_vars"]) if "local_vars" in info else "",
                   odd=True,
                   pre=True)

        _crash_row(_("Crash Type"), info["crash_type"], odd=False, legend=True)
        _crash_row(_("Time"),
                   time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["time"])),
                   odd=True)
        _crash_row(_("Operating System"), info["os"], False)
        _crash_row(_("Checkmk Version"), info["version"], True)
        _crash_row(_("Edition"), info.get("edition", ""), False)
        _crash_row(_("Core"), info.get("core", ""), True)
        _crash_row(_("Python Version"), info.get("python_version", _("Unknown")), False)

        joined_paths = "<br>".join(
            [html.attrencode(p) for p in info.get("python_paths", [_("Unknown")])])
        _crash_row(_("Python Module Paths"), joined_paths, odd=False)

        html.close_table()

    def _format_traceback(self, tb):
        return "".join(traceback.format_list(tb))

    def _show_crash_report_details(self, crash_info, row):
        # TODO: Cleanup different handlings
        # TODO: Handle new types
        if crash_info["crash_type"] == "check":
            _show_crashed_check_details(crash_info)
            _show_agent_output(row)
        elif crash_info["crash_type"] == "gui":
            _show_gui_crash_details(crash_info)
        else:
            raise NotImplementedError()


def _get_crash_report_row(crash_id, site_id):
    # TODO: Drop this once the livestatus table is ready
    from cmk.gui.plugins.views.crash_reporting import CrashReportsRowTable
    for row in CrashReportsRowTable()._crash_report_rows_from_local_site():
        if row["site"] == site_id and row["crash_id"] == crash_id:
            return row
    return None


def _crash_row(title, infotext, odd=True, legend=False, pre=False):
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
    return base64.b64decode(local_vars)


def _show_crashed_check_details(info):
    def format_bool(val):
        return {
            True: _("Yes"),
            False: _("No"),
            None: _("Unknown"),
        }[val]

    details = info["details"]

    html.h2(_("Details"))
    html.open_table(class_="data")

    _crash_row(_("Host"), details["host"], odd=False, legend=True)
    _crash_row(_("Is Cluster Host"), format_bool(details.get("is_cluster")), odd=True)
    _crash_row(_("Check Type"), details["check_type"], odd=False)
    _crash_row(_("Manual Check"), format_bool(details.get("manual_check")), odd=True, pre=True)
    _crash_row(_("Uses SNMP"), format_bool(details.get("uses_snmp")), odd=False, pre=True)
    _crash_row(_("Inline-SNMP"), format_bool(details.get("inline_snmp")), odd=True, pre=True)
    _crash_row(_("Check Item"), details["item"], odd=False)
    _crash_row(_("Description"), details["description"], odd=True)
    _crash_row(_("Parameters"), format_params(details["params"]), odd=False, pre=True)

    html.close_table()


def format_params(params):
    return pprint.pformat(params)


def _show_gui_crash_details(info):
    details = info["details"]

    html.h2(_("Details"))
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


def _show_agent_output(row):
    agent_output = row.get("agent_output")
    if agent_output:
        _show_output_box(_("Agent output"), agent_output)


def _show_output_box(title, content):
    html.h3(title)
    html.open_div(class_="log_output")
    html.write(html.attrencode(content).replace("\n", "<br>").replace(' ', '&nbsp;'))
    html.close_div()


@cmk.gui.pages.page_registry.register_page("download_crash_report")
class PageDownloadCrashReport(ABCCrashReportPage):
    def page(self):
        config.user.need_permission("general.see_crash_reports")

        filename = "Checkmk_Crash_%s_%s_%s.tar.gz" % \
            (html.urlencode(self._site_id), html.urlencode(self._crash_id), time.strftime("%Y-%m-%d_%H-%M-%S"))

        html.response.headers['Content-Disposition'] = 'Attachment; filename=%s' % filename
        html.response.headers['Content-Type'] = 'application/x-tar'
        html.write(_pack_crash_report(self._get_serialized_crash_report()))


def _pack_crash_report(serialized_crash_report):
    # type: (Dict) -> Text
    """Returns a byte string representing the current crash report in tar archive format"""
    buf = StringIO.StringIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        for key, content in serialized_crash_report.iteritems():
            tar_info = tarfile.TarInfo(name="crash.info" if key == "crash_info" else key)
            tar_info.size = len(content)

            tar.addfile(tar_info, StringIO.StringIO(content))

    return buf.getvalue()
