#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from typing import Any

from livestatus import SiteId

from cmk.utils.html import replace_state_markers
from cmk.utils.labels import Labels
from cmk.utils.rulesets.ruleset_matcher import LabelSources
from cmk.utils.tags import TaggroupID, TagID

import cmk.gui.utils.escaping as escaping
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import FilterHTTPVariables, HTTPVariables, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.labels import filter_http_vars_for_simple_label_group
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri, makeuri_contextless


class PythonExportError(Exception):
    pass


class CSVExportError(Exception):
    pass


class JSONExportError(Exception):
    pass


CSSClass = str | None
# Dict: The aggr_treestate painters are returning a dictionary data structure (see
# paint_aggregated_tree_state()) in case the output_format is not HTML. Once we have
# separated the data from rendering of the data, we can hopefully clean this up
CellContent = str | HTML | Mapping[str, Any]
CellSpec = tuple[CSSClass, CellContent]

# fmt: off
_URL_PATTERN = (
    r"("
    r"http[s]?://"
    r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*"  # including *all* sub-delimiters
    # In theory, URIs are allowed to end in a sub-delimitter ("!$&'()*+,;=")
    # We exclude the ',' here, because it is used to separate our check results,
    # and disallowing a trailing ',' hopefully breaks fewer links than allowing it.
    r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+;=%]"
    r")"
)
# fmt: on
_STATE_MARKER_PATTERN = r"(.*)(\((?:!|!!|.)\))$"


def format_plugin_output(output: str, row: Row | None = None, shall_escape: bool = True) -> HTML:
    shall_escape = _consolidate_escaping_options(row, shall_escape)

    if shall_escape and _render_url_icons(row):
        output = _normalize_check_http_link(output)
        output = _render_icon_button(output)
    elif shall_escape:
        output = escaping.escape_attribute(output)

    output = replace_state_markers(output)

    output = _render_host_links(output, row)

    return HTML(output)


def _consolidate_escaping_options(row: Row | None, shall_escape: bool) -> bool:
    # In case we have a host or service row use the optional custom attribute
    # ESCAPE_PLUGIN_OUTPUT (set by host / service ruleset) to override the global
    # setting.
    if row:
        custom_vars = row.get("service_custom_variables", row.get("host_custom_variables", {}))
        if "ESCAPE_PLUGIN_OUTPUT" in custom_vars:
            return custom_vars["ESCAPE_PLUGIN_OUTPUT"] == "1"
    return shall_escape


def _render_url_icons(row: Row | None) -> bool:
    return row is None or row.get("service_check_command", "") != "check_mk-checkmk_agent"


def _render_host_links(output: str, row: Row | None) -> str:
    if not row or "[running on" not in output:
        return output

    a = output.index("[running on")
    e = output.index("]", a)
    hosts = output[a + 12 : e].replace(" ", "").split(",")
    h = get_host_list_links(row["site"], hosts)
    return output[:a] + "running on " + ", ".join(h) + output[e + 1 :]


def _normalize_check_http_link(output: str) -> str:
    """Handling for the HTML code produced by check_http when "clickable URL" option is active"""
    if not (match := re.match('<A HREF="' + _URL_PATTERN + '" target="_blank">(.*?) </A>', output)):
        return output
    return f"{match.group(1)} {match.group(2)}"


def _render_icon_button(output: str) -> str:
    buffer = []
    for idx, token in enumerate(re.split(r"([\"']?)" + _URL_PATTERN + r"(\1)", output)):
        match idx % 4:
            case 0:
                buffer.append(escaping.escape_attribute(token))
            case 2:
                # if a url is directly followed by a state marker, separate them
                if match := re.match(_STATE_MARKER_PATTERN, token):
                    url, state_marker = match.group(1), match.group(2)
                    buffer.append(str(html.render_icon_button(url, url, "link", target="_blank")))
                    buffer.append(escaping.escape_attribute(state_marker))
                else:
                    buffer.append(
                        str(html.render_icon_button(token, token, "link", target="_blank"))
                    )
    return "".join(buffer)


def get_host_list_links(site: SiteId, hosts: list[str]) -> list[str]:
    entries = []
    for host in hosts:
        args: HTTPVariables = [
            ("view_name", "hoststatus"),
            ("site", site),
            ("host", host),
        ]

        if request.var("display_options"):
            args.append(("display_options", request.var("display_options")))

        url = makeuri_contextless(request, args, filename="view.py")
        link = str(HTMLWriter.render_a(host, href=url))
        entries.append(link)
    return entries


def row_limit_exceeded(row_count: int, limit: int | None) -> bool:
    return limit is not None and row_count >= limit + 1


def query_limit_exceeded_warn(limit: int | None, user_config: LoggedInUser) -> None:
    """Compare query reply against limits, warn in the GUI about incompleteness"""
    text = HTML(_("Your query produced more than %d results. ") % limit)

    if request.get_ascii_input("limit", "soft") == "soft" and user_config.may(
        "general.ignore_soft_limit"
    ):
        text += HTMLWriter.render_a(
            _("Repeat query and allow more results."),
            target="_self",
            href=makeuri(request, [("limit", "hard")]),
        )
    elif request.get_ascii_input("limit") == "hard" and user_config.may(
        "general.ignore_hard_limit"
    ):
        text += HTMLWriter.render_a(
            _("Repeat query without limit."),
            target="_self",
            href=makeuri(request, [("limit", "none")]),
        )

    text += escaping.escape_to_html_permissive(
        " " + _("<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
    )
    html.show_warning(text)


def get_labels(row: "Row", what: str) -> Labels:
    # Sites with old versions that don't have the labels column return
    # None for this field. Convert this to the default value
    labels = row.get("%s_labels" % what, {}) or {}
    assert isinstance(labels, dict)
    return labels


def render_labels(
    labels: Labels, object_type: str, with_links: bool, label_sources: LabelSources
) -> HTML:
    return _render_tag_groups_or_labels(
        labels, object_type, with_links, label_type="label", label_sources=label_sources
    )


def render_tag_groups(
    tag_groups: Mapping[TaggroupID, TagID], object_type: str, with_links: bool
) -> HTML:
    return _render_tag_groups_or_labels(
        tag_groups, object_type, with_links, label_type="tag_group", label_sources={}
    )


def _render_tag_groups_or_labels(
    entries: Mapping[TaggroupID, TagID] | Labels,
    object_type: str,
    with_links: bool,
    label_type: str,
    label_sources: LabelSources,
) -> HTML:
    elements = [
        _render_tag_group(
            tag_group_id_or_label_key,
            tag_id_or_label_value,
            object_type,
            with_links,
            label_type,
            label_sources.get(tag_group_id_or_label_key, "unspecified"),
        )
        for tag_group_id_or_label_key, tag_id_or_label_value in sorted(entries.items())
    ]
    return HTMLWriter.render_tags(
        HTML(" ").join(elements), class_=["tagify", label_type, "display"], readonly="true"
    )


def _render_tag_group(
    tag_group_id_or_label_key: TaggroupID | str,
    tag_id_or_label_value: TagID | str,
    object_type: str,
    with_link: bool,
    label_type: str,
    label_source: str,
) -> HTML:
    span = HTMLWriter.render_tag(
        HTMLWriter.render_div(
            HTMLWriter.render_span(
                "%s:%s"
                % (
                    tag_group_id_or_label_key,
                    tag_id_or_label_value,
                ),
                class_=["tagify__tag-text"],
            )
        ),
        class_=["tagify--noAnim", label_source],
    )
    if not with_link:
        return span

    if label_type == "tag_group":
        type_filter_vars: HTTPVariables = [
            ("%s_tag_0_grp" % object_type, tag_group_id_or_label_key),
            ("%s_tag_0_op" % object_type, "is"),
            ("%s_tag_0_val" % object_type, tag_id_or_label_value),
        ]
    elif label_type == "label":
        filter_vars_dict: FilterHTTPVariables = filter_http_vars_for_simple_label_group(
            [f"{tag_group_id_or_label_key}:{tag_id_or_label_value}"],
            object_type,  # type: ignore[arg-type]
        )
        type_filter_vars = list(filter_vars_dict.items())

    else:
        raise NotImplementedError()

    url_vars: HTTPVariables = [
        ("filled_in", "filter"),
        ("search", "Search"),
        ("view_name", "searchhost" if object_type == "host" else "searchsvc"),
    ]

    url = makeuri_contextless(request, url_vars + type_filter_vars, filename="view.py")
    return HTMLWriter.render_a(span, href=url)


def get_themed_perfometer_bg_color() -> str:
    """Return the theme specific background color for perfometer rendering"""
    if theme.get() == "modern-dark":
        return "#bdbdbd"
    # else (classic and modern theme)
    return "#ffffff"
