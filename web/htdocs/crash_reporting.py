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

import subprocess, base64, time, pprint, traceback, tarfile, cStringIO, sys
import inspect
from lib import *
from valuespec import *
import table, defaults, config, userdb, forms

try:
    import simplejson as json
except ImportError:
    import json

def page_crashed(what):
    if what == "check":
        site    = html.var("site")
        host    = html.var("host")
        service = html.var("service")

        tardata = get_crash_report_archive_as_string(site, host, service)
    else:
        tardata = create_gui_crash_report()

    info = get_crash_info(tardata)

    if what == "gui":
        title = _("Internal error")
    else:
        title = _("Crashed Check Reporting")

    html.header(title, stylesheets=["status", "pages"])

    show_context_buttons(what)

    if html.has_var("_report") and html.check_transaction():
        details = handle_report_form(tardata)
    else:
        details = {}

    if what == "gui":
        html.show_error("<b>%s:</b> %s" % (_("Internal error"), sys.exc_info()[1]))
        html.write("<p>%s</p>" %
                    _("An internal error occured while processing your request. "
                     "You can report this issue to the Check_MK team to help "
                     "fixing this issue. Please use the form below for reporting."))

    if info:
        warn_about_local_files(info)
        show_report_form(details)
        show_crash_report(info)
        show_crash_report_details(info)
    else:
        report_url = mailto_url = html.makeuri([
            ("subject", "Check_MK Crash Report - " + defaults.check_mk_version),
        ], filename="mailto:" + config.crash_report_target)
        html.message(_("This crash report is in a legacy format and can not be submitted "
                       "automatically. Please download it manually and send it to <a href=\"%s\">%s</a>")
                                % (report_url , config.crash_report_target))
        show_old_dump_trace(tardata)

    show_agent_output(tardata)

    html.footer()


def show_crash_report_details(info):
    if info["crash_type"] == "check":
        show_crashed_check_details(info)
    else:
        show_gui_crash_details(info)


def show_context_buttons(what):
    if what == "check":
        html.begin_context_buttons()
        site    = html.var("site")
        host    = html.var("host")
        service = html.var("service")

        host_url = html.makeuri([("view_name", "hoststatus"),
                                 ("host",      host),
                                 ("site",      site)], filename="view.py")
        html.context_button(_("Host status"), host_url, "status")

        host_url = html.makeuri([("view_name", "service"),
                                 ("host",      host),
                                 ("service",   service),
                                 ("site",      site)], filename="view.py")
        html.context_button(_("Service status"), host_url, "status")

        # FIXME: Make download possible for GUI crash reports
        download_url = html.makeuri([], filename="download_crash_report.py")
        html.context_button(_("Download"), download_url, "download")
        html.end_context_buttons()


def get_crash_report_archive_as_string(site, host, service):
    query = "GET services\n" \
            "Filter: host_name = %s\n" \
            "Filter: service_description = %s\n" \
            "Columns: long_plugin_output\n" % (
            lqencode(host), lqencode(service))

    html.live.set_only_sites([site])
    data = html.live.query_value(query)
    html.live.set_only_sites()

    if not data.startswith("Crash dump:\\n"):
        raise MKGeneralException("No crash dump is available for this service.")
    encoded_tardata = data[13:].rstrip()
    if encoded_tardata.endswith("\\n"):
        encoded_tardata = encoded_tardata[:-2]

    try:
        return base64.b64decode(encoded_tardata)
    except Exception, e:
        raise MKGeneralException("Encoded crash dump data is invalid: %s" % e)


def get_crash_info(tardata):
    info = fetch_file_from_tar(tardata, "crash.info")
    if info:
        return json.loads(info)


def fetch_file_from_tar(tardata, filename):
    p = subprocess.Popen(['tar', 'xzf', '-', '--to-stdout', filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = p.communicate(tardata)
    return result[0]


def output_box(title, content):
    html.write('<h3>%s</h3>' % title)
    html.write('<div class=log_output>%s</div>'
               % html.attrencode(content).replace("\n", "<br>").replace(' ', '&nbsp;'))


def vs_crash_report():
    return Dictionary(
        title = _("Crash Report"),
        elements = [
            ("name", TextUnicode(
                title = _("Name"),
                allow_empty = False,
            )),
            ("mail", EmailAddress(
                title = _("Email Address"),
                allow_empty = False,
            )),
        ],
        optional_keys = [],
        render = "form",
    )


def handle_report_form(tardata):
    details = {}
    try:
        vs = vs_crash_report()
        details = vs.from_html_vars("_report")
        vs.validate_value(details, "_report")

        # Make the resulting page execute the crash report post request
        url_encoded_params = html.urlencode_vars(details.items() + [
            ("crashdump", base64.b64encode(tardata)),
        ])
        html.write("<div id=\"pending_msg\" style=\"display:none\">")
        html.message(_("Submitting crash report..."))
        html.write("</div>")
        html.write("<div id=\"success_msg\" style=\"display:none\">")
        html.message(HTML(_(
            "Your crash report has been submitted (ID: ###ID###). Thanks for your participation, "
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
            "you find details on <a href=\"http://mathias-kettner.com/"
            "checkmk_support_contract.html\" target=_blank>our website</a>.")))
        html.write("</div>")
        html.write("<div id=\"fail_msg\" style=\"display:none\">")
        report_url = mailto_url = html.makeuri([
            ("subject", "Check_MK Crash Report - " + defaults.check_mk_version),
        ], filename="mailto:" + config.crash_report_target)
        html.show_error(_("Failed to send the crash report. Please download it manually and send it "
                          "to <a href=\"%s\">%s</a>") % (report_url , config.crash_report_target))
        html.write("</div>")
        html.javascript("submit_crash_report('https://mathias-kettner.de/crash_report.php', " \
                                            "'%s');" % url_encoded_params)
    except MKUserError, e:
        action_message = "%s" % e
        html.add_user_error(e.varname, action_message)

    return details


def warn_about_local_files(info):
    if info["crash_type"] == "check":
        files = []
        for filepath, lineno, func, line in info["exc_traceback"]:
            if "/local/" in filepath:
                files.append(filepath)

        if files:
            html.show_warning(HTML(
                _("The following files located in the local hierarchy of your site are "
                  "involved in this exception:")
               +"<ul>%s</ul>" % "\n".join([ "<li>%s</li>" % f for f in files ])
               +_("Maybe these files are not compatible with your current Check_MK "
                  "version. Please verify and only report this crash when you think "
                  "this should be working.")))


def show_report_form(details):
    users = userdb.load_users()
    user = users.get(config.user_id, {})
    details.setdefault("name", user.get("alias"))
    details.setdefault("mail", user.get("mail"))

    html.begin_form("report", method = "GET")
    html.show_user_errors()
    vs = vs_crash_report()
    vs.render_input("_report", details)
    vs.set_focus("report")
    forms.end()
    html.button("_report", _("Submit Report"))
    html.hidden_fields()
    html.end_form()


def show_crash_report(info):
    html.write("<h2>%s</h2>" % _("Crash Report"))
    html.write("<table class=\"data\">")
    html.write("<tr class=\"data even0\"><td class=\"left legend\">%s</td>" % _("Crash Type"))
    html.write("<td>%s</td></tr>" % html.attrencode(info["crash_type"]))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Time"))
    html.write("<td>%s</td></tr>" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["time"])))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Operating System"))
    html.write("<td>%s</td></tr>" % html.attrencode(info["os"]))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Check_MK Version"))
    html.write("<td>%s</td></tr>" % html.attrencode(info["version"]))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Python Version"))
    html.write("<td>%s</td></tr>" % html.attrencode(info.get("python_version", _("Unknown"))))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Exception"))
    html.write("<td><pre>%s (%s)</pre></td></tr>" % (html.attrencode(info["exc_type"]),
                                                     html.attrencode(info["exc_value"])))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Traceback"))
    html.write("<td><pre>%s</pre></td></tr>" % html.attrencode(format_traceback(info["exc_traceback"])))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Local Variables"))
    html.write("<td><pre>%s</pre></td></tr>" % html.attrencode(format_local_vars(info["local_vars"])))
    html.write("</table>")


# Local vars are a base64 encoded repr of the python dict containing the local vars of
# the exception context. Decode it!
def format_local_vars(local_vars):
    return base64.b64decode(local_vars)


def show_crashed_check_details(info):
    def format_bool(val):
        return {
            True  : _("Yes"),
            False : _("No"),
            None  : _("Unknown"),
        }[val]

    details = info["details"]
    html.write("<h2>%s</h2>" % _("Details"))
    html.write("<table class=\"data\">")

    html.write("<tr class=\"data even0\"><td class=\"left legend\">%s</td>" % _("Host"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["host"]))

    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Is Cluster Host"))
    html.write("<td>%s</td></tr>" % format_bool(details.get("is_cluster")))

    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Check Type"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["check_type"]))

    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Manual Check"))
    html.write("<td><pre>%s</pre></td></tr>" % format_bool(details.get("manual_check")))

    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Uses SNMP"))
    html.write("<td><pre>%s</pre></td></tr>" % format_bool(details.get("uses_snmp")))

    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Inline-SNMP"))
    html.write("<td><pre>%s</pre></td></tr>" % format_bool(details.get("inline_snmp")))

    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Check Item"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["item"]))

    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Description"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["description"]))

    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Parameters"))
    html.write("<td><pre>%s</pre></td></tr>" % html.attrencode(format_params(details["params"])))

    html.write("</table>")


def format_traceback(tb):
    return "\n".join(traceback.format_list(tb))


def format_params(params):
    return pprint.pformat(params)


def show_gui_crash_details(info):
    details = info["details"]
    html.write("<h2>%s</h2>" % _("Details"))
    html.write("<table class=\"data\">")
    html.write("<tr class=\"data even0\"><td class=\"left legend\">%s</td>" % _("Page"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["page"]))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Request Method"))
    html.write("<td>%s</td></tr>" % html.attrencode(details.get("request_method", _("Unknown"))))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("HTTP Parameters"))
    html.write("<td>")
    html.debug_vars(vars=details["vars"], hide_with_mouse=False)
    html.write("</td></tr>")
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Referer"))
    html.write("<td>%s</td></tr>" % html.attrencode(details.get("referer", _("Unknown"))))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Username"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["username"]))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("User Agent"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["user_agent"]))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Mobile GUI"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["is_mobile"]))
    html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("SSL"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["is_ssl_request"]))
    html.write("<tr class=\"data even0\"><td class=\"left\">%s</td>" % _("Language"))
    html.write("<td>%s</td></tr>" % html.attrencode(details["language"]))

    html.write("</table>")


def show_old_dump_trace(tardata):
    trace = fetch_file_from_tar(tardata, "./trace")
    tracelines = []
    for line in trace.splitlines():
        try:
            tracelines.append(line.decode('utf-8'))
        except:
            tracelines.append(repr(line))
    trace = "\r\n".join(tracelines)
    output_box(_("Crash Report"), trace)


def show_agent_output(tardata):
    agent_output = fetch_file_from_tar(tardata, "agent_output")
    if agent_output == "": # handle old tar format
        agent_output = fetch_file_from_tar(tardata, "./agent_output")
    if agent_output:
        output_box(_("Agent output"), agent_output)


def get_local_vars_of_last_exception():
    local_vars = {}
    for key, val in inspect.trace()[-1][0].f_locals.items():
        local_vars[key] = format_var_for_export(val)

    # This needs to be encoded as the local vars might contain binary data which can not be
    # transported using JSON.
    return base64.b64encode(format_var_for_export(pprint.pformat(local_vars), maxsize=5*1024*1024))


def format_var_for_export(val, maxdepth=4, maxsize=1024*1024):
    if maxdepth == 0:
        return "Max recursion depth reached"

    if isinstance(val, dict):
        val = val.copy()
        for item_key, item_val in val.items():
            val[item_key] = format_var_for_export(item_val, maxdepth-1)

    elif isinstance(val, list):
        val = val[:]
        for index, item in enumerate(val):
            val[index] = format_var_for_export(item, maxdepth-1)

    elif isinstance(val, tuple):
        new_val = ()
        for item in val:
            new_val += (format_var_for_export(item, maxdepth-1),)
        val = new_val

    # Check and limit size
    if type(val) in (str, unicode):
        size = len(val)
        if size > maxsize:
            val = val[:maxsize] + "... (%d bytes stripped)" % (size - maxsize)

    return val


# The default JSON encoder raises an exception when detecting unknown types. For the crash
# reporting it is totally ok to have some string representations of the objects.
class RobustJSONEncoder(json.JSONEncoder):
    # Are there cases where no __str__ is available? if so, we should do something like %r
    def default(self, o):
        return "%s" % o


# Slightly duplicate code with modules/check_mk_base.py. Maybe create some kind of central library?
def create_crash_dump_info_file(tar):
    exc_type, exc_value, exc_traceback = sys.exc_info()

    crash_info = {
        "crash_type"    : "gui",
        "time"          : time.time(),
        "os"            : get_os_info(),
        "version"       : defaults.check_mk_version,
        "python_version": sys.version,
        "exc_type"      : exc_type.__name__,
        "exc_value"     : "%s" % exc_value,
        "exc_traceback" : traceback.extract_tb(exc_traceback),
        "local_vars"    : get_local_vars_of_last_exception(),
        "details"    : {
            "page"           : html.myfile+".py",
            "vars"           : html.vars,
            "username"       : html.user,
            "user_agent"     : html.get_user_agent(),
            "referer"        : html.get_referer(),
            "is_mobile"      : html.is_mobile(),
            "is_ssl_request" : html.is_ssl_request(),
            "language"       : config.get_language(),
            "request_method" : html.request_method(),
        },
    }

    content = cStringIO.StringIO()
    content.write(json.dumps(crash_info, cls=RobustJSONEncoder))
    content.seek(0)

    tarinfo = tarfile.TarInfo(name="crash.info")
    content.seek(0, 2)
    tarinfo.size = content.tell()
    content.seek(0)
    tar.addfile(tarinfo=tarinfo, fileobj=content)


def get_os_info():
    if defaults.omd_root:
        return file(defaults.omd_root+"/share/omd/distro.info").readline().split("=", 1)[1].strip()
    elif os.path.exists("/etc/redhat-release"):
        return file("/etc/redhat-release").readline().strip()
    elif os.path.exists("/etc/SuSE-release"):
        return file("/etc/SuSE-release").readline().strip()
    else:
        info = {}
        for f in [ "/etc/os-release", "/etc/lsb-release" ]:
            if os.path.exists(f):
                for line in file(f).readlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
                break

        if info:
            return info
        else:
            return "UNKNOWN"


def create_gui_crash_report():
    c = cStringIO.StringIO()
    tar = tarfile.open(mode="w:gz", fileobj=c)

    create_crash_dump_info_file(tar)

    tar.close()
    s = c.getvalue()
    return s


def page_download_crash_report():
    site    = html.var("site")
    host    = html.var("host")
    service = html.var("service")

    filename = "Check_MK_Crash_%s_%s_%s.tar.gz" % \
        (html.urlencode(host), html.urlencode(service), time.strftime("%Y-%m-%d_%H-%M-%S"))

    tardata = get_crash_report_archive_as_string(site, host, service)
    html.set_http_header('Content-Disposition', 'Attachment; filename=%s' % filename)
    html.set_http_header('Content-Type', 'application/x-tar')
    html.write(tardata)
