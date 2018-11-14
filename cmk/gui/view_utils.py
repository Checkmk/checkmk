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

import re

from cmk.gui.i18n import _
from cmk.gui.globals import html


# There is common code with modules/events.py:format_plugin_output(). Please check
# whether or not that function needs to be changed too
# TODO(lm): Find a common place to unify this functionality.
def format_plugin_output(output, row=None, shall_escape=True):
    ok_marker = '<b class="stmark state0">OK</b>'
    warn_marker = '<b class="stmark state1">WARN</b>'
    crit_marker = '<b class="stmark state2">CRIT</b>'
    unknown_marker = '<b class="stmark state3">UNKN</b>'

    # In case we have a host or service row use the optional custom attribute
    # ESCAPE_PLUGIN_OUTPUT (set by host / service ruleset) to override the global
    # setting.
    if row:
        custom_vars = row.get("service_custom_variables", row.get("host_custom_variables", {}))
        if "ESCAPE_PLUGIN_OUTPUT" in custom_vars:
            shall_escape = custom_vars["ESCAPE_PLUGIN_OUTPUT"] == "1"

    if shall_escape:
        output = html.attrencode(output)

    output = output.replace("(!)", warn_marker) \
              .replace("(!!)", crit_marker) \
              .replace("(?)", unknown_marker) \
              .replace("(.)", ok_marker)

    if row and "[running on" in output:
        a = output.index("[running on")
        e = output.index("]", a)
        hosts = output[a + 12:e].replace(" ", "").split(",")
        h = get_host_list_links(row["site"], hosts)
        output = output[:a] + "running on " + ", ".join(h) + output[e + 1:]

    if shall_escape:
        http_url = r"(http[s]?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)"
        # (?:&lt;A HREF=&quot;), (?: target=&quot;_blank&quot;&gt;)? and endswith(" </A>") is a special
        # handling for the HTML code produced by check_http when "clickable URL" option is active.
        output = re.sub("(?:&lt;A HREF=&quot;)?" + http_url + "(?: target=&quot;_blank&quot;&gt;)?",
                         lambda p: '<a href="%s"><img class=pluginurl align=absmiddle title="%s" src="images/pluginurl.png"></a>' %
                            (p.group(1).replace('&quot;', ''), p.group(1).replace('&quot;', '')), output)

        if output.endswith(" &lt;/A&gt;"):
            output = output[:-11]

    return output


def get_host_list_links(site, hosts):
    entries = []
    for host in hosts:
        args = [
            ("view_name", "hoststatus"),
            ("site", site),
            ("host", host),
        ]

        if html.var("display_options"):
            args.append(("display_options", html.var("display_options")))

        url = html.makeuri_contextless(args, filename="view.py")
        link = unicode(html.render_a(host, href=url))
        entries.append(link)
    return entries


def check_limit(rows, limit, user):
    count = len(rows)
    if limit != None and count >= limit + 1:
        text = _("Your query produced more than %d results. ") % limit

        if html.get_ascii_input("limit",
                                "soft") == "soft" and user.may("general.ignore_soft_limit"):
            text += html.render_a(
                _('Repeat query and allow more results.'),
                target="_self",
                href=html.makeuri([("limit", "hard")]))
        elif html.get_ascii_input("limit") == "hard" and user.may("general.ignore_hard_limit"):
            text += html.render_a(
                _('Repeat query without limit.'),
                target="_self",
                href=html.makeuri([("limit", "none")]))

        text += " " + _(
            "<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
        html.show_warning(text)
        del rows[limit:]
        return False
    return True
