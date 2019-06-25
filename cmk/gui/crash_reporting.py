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

import os
import subprocess
import base64
import time
import pprint
import traceback
import tarfile
import cStringIO
import sys
import json
import livestatus

import cmk.gui.pages
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.userdb as userdb
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.valuespec import (
    EmailAddress,
    TextUnicode,
    Dictionary,
)
import cmk.gui.config as config
import cmk.gui.forms as forms
import cmk.utils.crash_reporting


@cmk.gui.pages.register("crashed_check")
def page_crashed_check():
    page_crashed("check")


@cmk.gui.pages.register("gui_crash")
def page_gui_crash():
    page_crashed("gui")


def page_crashed(what):
    # Do not reveal crash context information to unauthenticated users or not permitted
    # users to prevent disclosure of internal information
    if not config.user.may("general.see_crash_reports"):
        html.header(_("Internal error"))
        html.show_error("<b>%s:</b> %s" % (_("Internal error"), sys.exc_info()[1]))
        html.p(
            _("An internal error occurred while processing your request. "
              "You can report this issue to your Check_MK administrator. "
              "Detailed information can be found in <tt>var/log/web.log</tt>."))
        html.footer()
        return

    if what == "check":
        site = html.request.var("site")
        host = html.request.var("host")
        service = html.request.var("service")

        tardata = get_crash_report_archive_as_string(site, host, service)
    else:
        tardata = create_gui_crash_report(what)

    info = get_crash_info(tardata)

    if what == "check":
        title = _("Crashed Check Reporting")
    else:
        title = _("Internal error")

    html.header(title)

    show_context_buttons(what, tardata)

    if html.request.has_var("_report") and html.check_transaction():
        details = handle_report_form(tardata, what)
    else:
        details = {}

    if what == "gui":
        # Unify different string types from exception messages to a unicode string
        exc_value = sys.exc_info()[1]
        try:
            exc_txt = unicode(exc_value)
        except UnicodeDecodeError:
            exc_txt = str(exc_value).decode("utf-8")

        html.show_error("<b>%s:</b> %s" % (_("Internal error"), exc_txt))
        html.p(
            _("An internal error occured while processing your request. "
              "You can report this issue to the Check_MK team to help "
              "fixing this issue. Please use the form below for reporting."))

    if info:
        warn_about_local_files(info)
        show_report_form(what, details)
        show_crash_report(info)
        show_crash_report_details(info)
    else:
        report_url = html.makeuri([("subject", "Check_MK Crash Report - " + get_version(what))],
                                  filename="mailto:" + get_crash_report_target(what))
        html.message(
            _("This crash report is in a legacy format and can not be submitted "
              "automatically. Please download it manually and send it to <a href=\"%s\">%s</a>") %
            (report_url, get_crash_report_target(what)))
        show_old_dump_trace(tardata)

    show_agent_output(tardata)

    html.footer()


def show_crash_report_details(info):
    if info["crash_type"] == "check":
        show_crashed_check_details(info)
    else:
        show_gui_crash_details(info)


def show_context_buttons(what, tardata):
    html.begin_context_buttons()
    if what == "check":
        site = html.request.var("site")
        host = html.request.var("host")
        service = html.request.var("service")

        host_url = html.makeuri([("view_name", "hoststatus"), ("host", host), ("site", site)],
                                filename="view.py")
        html.context_button(_("Host status"), host_url, "status")

        host_url = html.makeuri([("view_name", "service"), ("host", host), ("service", service),
                                 ("site", site)],
                                filename="view.py")
        html.context_button(_("Service status"), host_url, "status")

        download_url = html.makeuri([], filename="download_crash_report.py")
        html.context_button(_("Download"), download_url, "download")

    elif what == "gui":
        download_data_url = "data:application/octet-stream;base64,%s" % base64.b64encode(tardata)
        html.context_button(
            _("Download"), "javascript:cmk.crash_reporting.download('%s')" % download_data_url,
            "download")

    html.end_context_buttons()


def get_crash_report_archive_as_string(site, host, service):
    query = "GET services\n" \
            "Filter: host_name = %s\n" \
            "Filter: service_description = %s\n" \
            "Columns: long_plugin_output\n" % (
            livestatus.lqencode(host), livestatus.lqencode(service))

    sites.live().set_only_sites([site])
    data = sites.live().query_value(query)
    sites.live().set_only_sites()

    if not data.startswith("Crash dump:\\n"):
        raise MKGeneralException("No crash dump is available for this service.")
    encoded_tardata = data[13:].rstrip()
    if encoded_tardata.endswith("\\n"):
        encoded_tardata = encoded_tardata[:-2]

    try:
        return base64.b64decode(encoded_tardata)
    except Exception as e:
        raise MKGeneralException("Encoded crash dump data is invalid: %s" % e)


def get_crash_info(tardata):
    info = fetch_file_from_tar(tardata, "crash.info")
    if info:
        return json.loads(info)


def fetch_file_from_tar(tardata, filename):
    p = subprocess.Popen(['tar', 'xzf', '-', '--to-stdout', filename],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=open(os.devnull, "w"),
                         close_fds=True)
    result = p.communicate(tardata)
    return result[0]


def output_box(title, content):
    html.h3(title)
    html.open_div(class_="log_output")
    html.write(html.attrencode(content).replace("\n", "<br>").replace(' ', '&nbsp;'))
    html.close_div()


def vs_crash_report():
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


def handle_report_form(tardata, what):
    details = {}
    try:
        vs = vs_crash_report()
        details = vs.from_html_vars("_report")
        vs.validate_value(details, "_report")

        # Make the resulting page execute the crash report post request
        url_encoded_params = html.urlencode_vars(details.items() + [
            ("crashdump", base64.b64encode(tardata)),
        ])
        html.open_div(id_="pending_msg", style="display:none")
        html.message(_("Submitting crash report..."))
        html.close_div()
        html.open_div(id_="success_msg", style="display:none")
        html.message(
            _("Your crash report has been submitted (ID: ###ID###). Thanks for your participation, "
              "it is very important for the quality of Check_MK.<br><br>"
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
            ("subject", "Check_MK Crash Report - " + get_version(what)),
        ],
                                  filename="mailto:" + get_crash_report_target(what))
        html.show_error(
            _("Failed to send the crash report. Please download it manually and send it "
              "to <a href=\"%s\">%s</a>") % (report_url, get_crash_report_target(what)))
        html.close_div()
        html.javascript("cmk.crash_reporting.submit('https://checkmk.com/crash_report.php', " \
                                            "'%s');" % url_encoded_params)
    except MKUserError as e:
        action_message = "%s" % e
        html.add_user_error(e.varname, action_message)

    return details


# TODO: Would be cleaner to override if we used OOP
def get_crash_report_target(what):
    if what == "cma":
        return "feedback@checkmk.com"
    return config.crash_report_target


# TODO: Would be cleaner to override if we used OOP
def get_version(what):
    if what == "cma":
        import cma  # pylint: disable=import-error
        return cma.version()
    return cmk.__version__


def warn_about_local_files(info):
    if info["crash_type"] == "check":
        files = []
        for filepath, _lineno, _func, _line in info["exc_traceback"]:
            if "/local/" in filepath:
                files.append(filepath)

        if files:
            warn_text = _(
                "The following files located in the local hierarchy of your site are involved in this exception:"
            )
            warn_text += html.render_ul(HTML("\n").join(map(html.render_li, files)))
            warn_text += _("Maybe these files are not compatible with your current Check_MK "
                           "version. Please verify and only report this crash when you think "
                           "this should be working.")
            html.show_warning(warn_text)


def show_report_form(what, details):
    if what == "gui":
        add_gui_user_infos_to_details(details)

    html.begin_form("report", method="GET")
    html.show_user_errors()
    vs = vs_crash_report()
    vs.render_input("_report", details)
    vs.set_focus("report")
    forms.end()
    html.button("_report", _("Submit Report"))
    html.hidden_fields()
    html.end_form()


def add_gui_user_infos_to_details(details):
    users = userdb.load_users()
    user = users.get(config.user.id, {})
    details.setdefault("name", user.get("alias"))
    details.setdefault("mail", user.get("mail"))


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


def show_crash_report(info):

    html.h2(_("Crash Report"))
    html.open_table(class_=["data", "crash_report"])

    _crash_row(
        _("Exception"), "%s (%s)" % (info["exc_type"], info["exc_value"]), odd=True, pre=True)
    _crash_row(_("Traceback"), format_traceback(info["exc_traceback"]), odd=False, pre=True)
    _crash_row(
        _("Local Variables"),
        format_local_vars(info["local_vars"]) if "local_vars" in info else "",
        odd=True,
        pre=True)

    _crash_row(_("Crash Type"), info["crash_type"], odd=False, legend=True)
    _crash_row(
        _("Time"), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["time"])), odd=True)
    _crash_row(_("Operating System"), info["os"], False)
    if info["crash_type"] == "cma":
        version_title = _("CMA Version")
    else:
        version_title = _("Check_MK Version")
    _crash_row(version_title, info["version"], True)
    _crash_row(_("Edition"), info.get("edition", ""), False)
    _crash_row(_("Core"), info.get("core", ""), True)
    _crash_row(_("Python Version"), info.get("python_version", _("Unknown")), False)

    joined_paths = "<br>".join(
        [html.attrencode(p) for p in info.get("python_paths", [_("Unknown")])])
    _crash_row(_("Python Module Paths"), joined_paths, odd=False)

    html.close_table()


# Local vars are a base64 encoded repr of the python dict containing the local vars of
# the exception context. Decode it!
def format_local_vars(local_vars):
    return base64.b64decode(local_vars)


def show_crashed_check_details(info):
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


def format_traceback(tb):
    return "".join(traceback.format_list(tb))


def format_params(params):
    return pprint.pformat(params)


def show_gui_crash_details(info):
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


def show_old_dump_trace(tardata):
    trace = fetch_file_from_tar(tardata, "./trace")
    tracelines = []
    for line in trace.splitlines():
        try:
            tracelines.append(line.decode('utf-8'))
        except UnicodeDecodeError:
            tracelines.append(repr(line))
    trace = "\r\n".join(tracelines)
    output_box(_("Crash Report"), trace)


def show_agent_output(tardata):
    agent_output = fetch_file_from_tar(tardata, "agent_output")
    if agent_output == "":  # handle old tar format
        agent_output = fetch_file_from_tar(tardata, "./agent_output")
    if agent_output:
        output_box(_("Agent output"), agent_output)


def create_crash_dump_info_file(tar, what):
    crash_info = cmk.utils.crash_reporting.create_crash_info(
        what,
        details={
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
        },
        version=get_version(what))

    content = cStringIO.StringIO()
    content.write(cmk.utils.crash_reporting.crash_info_to_string(crash_info))
    content.seek(0)

    tarinfo = tarfile.TarInfo(name="crash.info")
    content.seek(0, os.SEEK_END)
    tarinfo.size = content.tell()
    content.seek(0)
    tar.addfile(tarinfo=tarinfo, fileobj=content)


def create_gui_crash_report(what):
    c = cStringIO.StringIO()
    tar = tarfile.open(mode="w:gz", fileobj=c)

    create_crash_dump_info_file(tar, what)

    tar.close()
    s = c.getvalue()
    return s


@cmk.gui.pages.register("download_crash_report")
def page_download_crash_report():
    site = html.request.var("site")
    host = html.request.var("host")
    service = html.request.var("service")

    filename = "Check_MK_Crash_%s_%s_%s.tar.gz" % \
        (html.urlencode(host), html.urlencode(service), time.strftime("%Y-%m-%d_%H-%M-%S"))

    tardata = get_crash_report_archive_as_string(site, host, service)
    html.response.headers['Content-Disposition'] = 'Attachment; filename=%s' % filename
    html.response.headers['Content-Type'] = 'application/x-tar'
    html.write(tardata)
