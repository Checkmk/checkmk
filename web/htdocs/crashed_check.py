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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import subprocess
from lib import *
import table, defaults, config

def fetch_file_from_tar(tardata, filename):
    p = subprocess.Popen(['tar', 'xzf', '-', '--to-stdout', filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = p.communicate(tardata)
    return result[0]

def output_box(title, content):
    html.write('<h3>%s</h3>' % title)
    html.write('<div class=log_output>%s</div>'
               % html.attrencode(content).replace("\n", "<br>"))

def page_crashed_check():
    html.header(_("Crashed Check Report"), stylesheets=["status", "pages",])

    site    = html.var("site")
    host    = html.var("host")
    service = html.var("service")

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
    import base64
    encoded_tardata = data[13:].rstrip()
    if encoded_tardata.endswith("\\n"):
        encoded_tardata = encoded_tardata[:-2]
    try:
        tardata = base64.b64decode(encoded_tardata)
    except Exception, e:
        raise MKGeneralException("Encoded crash dump data is invalid: %s" % e)

    trace = fetch_file_from_tar(tardata, "./trace")
    tracelines = []
    for line in trace.splitlines():
        try:
            tracelines.append(line.decode('utf-8'))
        except:
            tracelines.append(repr(line))
    trace = "\r\n".join(tracelines)

    agent_output = fetch_file_from_tar(tardata, "./agent_output")

    body =   "Dear Check_MK Developer team,\r\n\r\n" \
           + "I hereby send you a report of a crashed check:\r\n\r\n" \
           + trace.decode('utf-8') + "\r\n" \
           + "BASE64 encoded tarball with agent output:" \
           + "\r\n\r\n\r\n" + encoded_tardata \
           + "\r\n\r\nWith best regards,\r\n\r\n"

    html.begin_context_buttons()
    mailto_url = html.makeuri([("subject", "Check_MK Crash Report - " + defaults.check_mk_version),
                               ("body", body)], filename="mailto:" + config.crash_report_target)
    html.context_button(_("Submit Report"), mailto_url, "email")
    html.end_context_buttons()

    output_box(_("Crash report"), trace.replace(" ", "&nbsp;"))

    if agent_output:
        output_box(_("Agent output"), agent_output)

    html.footer()
