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
import json

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML


# There is common code with cmk/notification_plugins/utils.py:format_plugin_output(). Please check
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
        output = re.sub(
            "(?:&lt;A HREF=&quot;)?" + http_url +
            "(?: target=&quot;_blank&quot;&gt;)?", lambda p: str(
                html.render_icon_button(
                    p.group(1).replace('&quot;', ''),
                    p.group(1).replace('&quot;', ''), "link")), output)

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

        if html.request.var("display_options"):
            args.append(("display_options", html.request.var("display_options")))

        url = html.makeuri_contextless(args, filename="view.py")
        link = unicode(html.render_a(host, href=url))
        entries.append(link)
    return entries


def row_limit_exceeded(rows, limit):
    return limit is not None and len(rows) >= limit + 1


def query_limit_exceeded_with_warn(rows, limit, user_config):
    """Compare query reply against limits, warn in the GUI about incompleteness"""
    if not row_limit_exceeded(rows, limit):
        return False

    text = _("Your query produced more than %d results. ") % limit

    if html.get_ascii_input("limit",
                            "soft") == "soft" and user_config.may("general.ignore_soft_limit"):
        text += html.render_a(
            _('Repeat query and allow more results.'),
            target="_self",
            href=html.makeuri([("limit", "hard")]))
    elif html.get_ascii_input("limit") == "hard" and user_config.may("general.ignore_hard_limit"):
        text += html.render_a(
            _('Repeat query without limit.'),
            target="_self",
            href=html.makeuri([("limit", "none")]))

    text += " " + _(
        "<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
    html.show_warning(text)
    return True


def render_labels(labels, object_type, with_links, label_sources):
    return _render_tag_groups_or_labels(
        labels, object_type, with_links, label_type="label", label_sources=label_sources)


def render_tag_groups(tag_groups, object_type, with_links):
    return _render_tag_groups_or_labels(
        tag_groups, object_type, with_links, label_type="tag_group", label_sources={})


def _render_tag_groups_or_labels(entries, object_type, with_links, label_type, label_sources):
    elements = [
        _render_tag_group(tg_id, tag, object_type, with_links, label_type,
                          label_sources.get(tg_id, "unspecified"))
        for tg_id, tag in sorted(entries.items())
    ]
    return html.render_tags(
        HTML("").join(elements), class_=["tagify", label_type, "display"], readonly="true")


def _render_tag_group(tg_id, tag, object_type, with_link, label_type, label_source):
    span = html.render_tag(
        html.render_div(html.render_span("%s:%s" % (tg_id, tag), class_=["tagify__tag-text"])),
        class_=["tagify--noAnim", label_source])
    if not with_link:
        return span

    if label_type == "tag_group":
        type_filter_vars = [
            ("%s_tag_0_grp" % object_type, tg_id),
            ("%s_tag_0_op" % object_type, "is"),
            ("%s_tag_0_val" % object_type, tag),
        ]
    elif label_type == "label":
        type_filter_vars = [
            ("%s_label" % object_type, json.dumps([{
                "value": "%s:%s" % (tg_id, tag)
            }]).decode("utf-8")),
        ]

    else:
        raise NotImplementedError()

    url = html.makeuri_contextless(
        [
            ("filled_in", "filter"),
            ("search", "Search"),
            ("view_name", "searchhost" if object_type == "host" else "searchsvc"),
        ] + type_filter_vars,
        filename="view.py")
    return html.render_a(span, href=url)
