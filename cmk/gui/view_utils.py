#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import json
from typing import (  # pylint: disable=unused-import
    TYPE_CHECKING, Optional, Tuple, Union, Text, List, Any, Dict,
)
import six

from livestatus import SiteId  # pylint: disable=unused-import

from cmk.utils.type_defs import Labels, LabelSources, TagGroups, TagID, TagValue  # pylint: disable=unused-import
from cmk.utils.encoding import ensure_unicode

import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.utils.url_encoder import HTTPVariables  # pylint: disable=unused-import

CSSClass = str
# Dict: The aggr_treestate painters are returning a dictionary data structure (see
# paint_aggregated_tree_state()) in case the output_format is not HTML. Once we have
# separated the data from rendering of the data, we can hopefully clean this up
CellContent = Union[Text, str, HTML, Dict[str, Any]]
CellSpec = Tuple[CSSClass, CellContent]

if TYPE_CHECKING:
    from cmk.gui.type_defs import Row  # pylint: disable=unused-import
    from cmk.gui.config import LoggedInUser  # pylint: disable=unused-import


# There is common code with cmk/notification_plugins/utils.py:format_plugin_output(). Please check
# whether or not that function needs to be changed too
# TODO(lm): Find a common place to unify this functionality.
def format_plugin_output(output, row=None, shall_escape=True):
    # type: (CellContent, Optional[Row], bool) -> Text
    assert not isinstance(output, dict)
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
        output = escaping.escape_attribute(output)
    else:
        output = ensure_unicode("%s" % output)

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
            "(?:&lt;A HREF=&quot;)?" + http_url + "(?: target=&quot;_blank&quot;&gt;)?",
            lambda p: str(
                html.render_icon_button(
                    p.group(1).replace('&quot;', ''),
                    p.group(1).replace('&quot;', ''), "link")), output)

        if output.endswith(" &lt;/A&gt;"):
            output = output[:-11]

    return output


def get_host_list_links(site, hosts):
    # type: (SiteId, List[Union[Text, str]]) -> List[Text]
    entries = []
    for host in hosts:
        args = [
            ("view_name", "hoststatus"),
            ("site", site),
            ("host", host),
        ]  # type: HTTPVariables

        if html.request.var("display_options"):
            args.append(("display_options", html.request.var("display_options")))

        url = html.makeuri_contextless(args, filename="view.py")
        link = six.text_type(html.render_a(host, href=url))
        entries.append(link)
    return entries


def row_limit_exceeded(row_count, limit):
    # type: (int, Optional[int]) -> bool
    return limit is not None and row_count >= limit + 1


def query_limit_exceeded_warn(limit, user_config):
    # type: (Optional[int], LoggedInUser) -> None
    """Compare query reply against limits, warn in the GUI about incompleteness"""
    text = HTML(_("Your query produced more than %d results. ") % limit)

    if html.request.get_ascii_input(
            "limit", "soft") == "soft" and user_config.may("general.ignore_soft_limit"):
        text += html.render_a(_('Repeat query and allow more results.'),
                              target="_self",
                              href=html.makeuri([("limit", "hard")]))
    elif html.request.get_ascii_input("limit") == "hard" and user_config.may(
            "general.ignore_hard_limit"):
        text += html.render_a(_('Repeat query without limit.'),
                              target="_self",
                              href=html.makeuri([("limit", "none")]))

    text += " " + _(
        "<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
    html.show_warning(text)


def get_labels(row, what):
    # type: (Row, str) -> Labels
    # Sites with old versions that don't have the labels column return
    # None for this field. Convert this to the default value
    labels = row.get("%s_labels" % what, {}) or {}
    assert isinstance(labels, dict)
    return labels


def render_labels(labels, object_type, with_links, label_sources):
    # type: (Labels, str, bool, LabelSources) -> HTML
    return _render_tag_groups_or_labels(labels,
                                        object_type,
                                        with_links,
                                        label_type="label",
                                        label_sources=label_sources)


def render_tag_groups(tag_groups, object_type, with_links):
    # type: (TagGroups, str, bool) -> HTML
    return _render_tag_groups_or_labels(tag_groups,
                                        object_type,
                                        with_links,
                                        label_type="tag_group",
                                        label_sources={})


def _render_tag_groups_or_labels(entries, object_type, with_links, label_type, label_sources):
    # type: (Union[TagGroups, Labels], str, bool, str, LabelSources) -> HTML
    elements = [
        _render_tag_group(tg_id, tag, object_type, with_links, label_type,
                          label_sources.get(tg_id, "unspecified"))
        for tg_id, tag in sorted(entries.items())
    ]
    return html.render_tags(HTML("").join(elements),
                            class_=["tagify", label_type, "display"],
                            readonly="true")


def _render_tag_group(tg_id, tag, object_type, with_link, label_type, label_source):
    # type: (Union[TagID, Text], Union[TagValue, Text], str, bool, str, str) -> HTML
    span = html.render_tag(html.render_div(
        html.render_span("%s:%s" % (tg_id, tag), class_=["tagify__tag-text"])),
                           class_=["tagify--noAnim", label_source])
    if not with_link:
        return span

    if label_type == "tag_group":
        type_filter_vars = [
            ("%s_tag_0_grp" % object_type, tg_id),
            ("%s_tag_0_op" % object_type, "is"),
            ("%s_tag_0_val" % object_type, tag),
        ]  # type: HTTPVariables
    elif label_type == "label":
        type_filter_vars = [
            ("%s_label" % object_type,
             ensure_unicode(json.dumps([{
                 "value": "%s:%s" % (tg_id, tag)
             }]))),
        ]

    else:
        raise NotImplementedError()

    url_vars = [
        ("filled_in", "filter"),
        ("search", "Search"),
        ("view_name", "searchhost" if object_type == "host" else "searchsvc"),
    ]  # type: HTTPVariables

    url = html.makeuri_contextless(url_vars + type_filter_vars, filename="view.py")
    return html.render_a(span, href=url)


def get_themed_perfometer_bg_color():
    # type: () -> str
    """Return the theme specific background color for perfometer rendering"""
    if html.get_theme() == "modern-dark":
        return "#bdbdbd"
    # else (classic and modern theme)
    return "#ffffff"
