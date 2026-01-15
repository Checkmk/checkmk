#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"

import re
from collections.abc import Iterator, Mapping
from typing import Any, Literal

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import FilterHTTPVariables, HTTPVariables, IconNames, Row, StaticIcon
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.labels import filter_http_vars_for_simple_label_group
from cmk.gui.utils.loading_transition import with_loading_transition
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.utils.html import replace_state_markers
from cmk.utils.labels import LabelGroups, Labels, LabelSource, LabelSources
from cmk.utils.tags import TagGroupID, TagID


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

# We support more label CSS classes than just label sources
LabelRenderType = Literal[LabelSource, "changed", "removed", "added", "unspecified"]

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


def determine_must_escape(config: Config, row: Row) -> bool:
    """determine if we must escape the output

    When the row comes from a remote site the output might be malicious. We don't care if that site
    is trusted. To determine if the site is trusted we need the origin site that is sometimes stored
    in the Row and sometimes not.
    Due to some bugs that were introduced with the original Change (Werk #17998) fixs: Werk #18953
    and Werk #18952, we decided to be more robust."""

    if "site" not in row:
        # We have no idea if the origin site is trusted
        return True

    if (siteid := row["site"]) not in config.sites:
        logger.warning("Unknown siteid in row: %r", siteid)
        return True

    return not config.sites[row["site"]]["is_trusted"]


def format_plugin_output(
    output: str,
    *,
    request: Request,
    must_escape: bool,
    row: Row | None = None,
    shall_escape: bool = True,
    newlineishs_to_brs: bool = False,
) -> HTML:
    shall_escape = must_escape or _consolidate_escaping_options(row, shall_escape)

    if shall_escape and _render_url_icons(row):
        output = _normalize_check_http_link(output)
        output = _render_icon_button(output)
    elif shall_escape:
        output = escaping.escape_attribute(output)

    output = replace_state_markers(output)

    output = _render_host_links(output, row, request=request)

    if newlineishs_to_brs:
        output = output.replace("\\n", "<br>").replace("\n", "<br>")
    return HTML.without_escaping(output)


def _consolidate_escaping_options(row: Row | None, shall_escape: bool) -> bool:
    # In case we have a host or service row use the optional custom attribute
    # ESCAPE_PLUGIN_OUTPUT (set by host / service ruleset) to override the global
    # setting.
    if row:
        host_custom_variables: dict = row.get("host_custom_variables", {})
        custom_variables = row.get("service_custom_variables", host_custom_variables)
        if "ESCAPE_PLUGIN_OUTPUT" in custom_variables:
            escape_plugin_output: bool = custom_variables["ESCAPE_PLUGIN_OUTPUT"] == "1"
            return escape_plugin_output
    return shall_escape


def _render_url_icons(row: Row | None) -> bool:
    return row is None or row.get("service_check_command", "") != "check_mk-checkmk_agent"


def _render_host_links(output: str, row: Row | None, *, request: Request) -> str:
    if not row or "[running on" not in output:
        return output

    a = output.index("[running on")
    e = output.index("]", a)
    hosts = output[a + 12 : e].replace(" ", "").split(",")
    h = get_host_list_links(row["site"], hosts, request=request)
    return output[:a] + "running on " + ", ".join(map(str, h)) + output[e + 1 :]


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
                buffer.extend(_render_url(token, buffer[-1][-1] if buffer and buffer[-1] else ""))
    return "".join(buffer)


def _render_url(token: str, last_char: str) -> Iterator[str]:
    url = token
    rest: str | None = None

    # if a url is directly followed by a state marker, separate them
    if match := re.match(_STATE_MARKER_PATTERN, token):
        url, rest = match.group(1), match.group(2)

    # A URL may be surrounded by parantheses without spaces.
    # Since ")" and ":" are allowed in URLS, we have to detect this situation explicitly.
    elif last_char == "(":
        if token.endswith(")"):
            url, rest = token[:-1], ")"
        elif token.endswith("):"):
            url, rest = token[:-2], "):"

    yield str(html.render_icon_button(url, url, StaticIcon(IconNames.link), target="_blank"))
    if rest is not None:
        yield escaping.escape_attribute(rest)


def get_host_list_links(site: SiteId, hosts: list[str], *, request: Request) -> list[HTML]:
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
        link = HTMLWriter.render_a(host, href=url)
        entries.append(link)
    return entries


def row_limit_exceeded(row_count: int, limit: int | None) -> bool:
    return limit is not None and row_count >= limit + 1


def query_limit_exceeded_warn(limit: int | None, user_config: LoggedInUser) -> None:
    """Compare query reply against limits, warn in the GUI about incompleteness"""
    text = HTML.with_escaping(_("Your query produced more than %d results. ") % limit)

    ignore_limit_link = None
    if request.get_ascii_input("limit", "soft") == "soft" and user_config.may(
        "general.ignore_soft_limit"
    ):
        ignore_limit_link = HTMLWriter.render_a(
            _("Repeat query and allow more results."),
            target="_self",
            href=makeuri(request, [("limit", "hard")]),
        )
    elif request.get_ascii_input("limit") == "hard" and user_config.may(
        "general.ignore_hard_limit"
    ):
        ignore_limit_link = HTMLWriter.render_a(
            _("Repeat query without limit."),
            target="_self",
            href=makeuri(request, [("limit", "none")]),
        )

    if ignore_limit_link is not None:
        text += with_loading_transition(ignore_limit_link, template=None)

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
    labels: Labels,
    object_type: str,
    with_links: bool,
    label_sources: LabelSources,
    override_label_render_type: LabelRenderType | None = None,
    *,
    request: Request,
) -> HTML:
    return _render_tag_groups_or_labels(
        labels,
        object_type,
        with_links,
        label_type="label",
        label_sources=label_sources,
        override_label_render_type=override_label_render_type,
        request=request,
    )


def render_label_groups(label_groups: LabelGroups, object_type: str) -> HTML:
    overall_html = HTML.empty()

    is_first_group: bool = True
    for group_op, label_group in label_groups:
        group_html = HTML.empty()

        # Render group operator
        if not is_first_group:
            group_op_str = "and not" if group_op == "not" else group_op  # prepend "not" with "and "
            overall_html += (
                " " + HTMLWriter.render_i(group_op_str, class_="andornot_operator") + " "
            )

        group_html += "["  # open group

        is_first_label: bool = True
        for label_op, label in label_group:
            if not label:
                continue

            # Render label operator
            if not is_first_label or label_op == "not":
                # Prepend "not" with "and " if the current is not the first label
                label_op_str = "and not" if (not is_first_label and label_op == "not") else label_op
                group_html += HTMLWriter.render_i(label_op_str, class_="andornot_operator")

            # Render single label
            key, val = label.split(":")
            group_html += HTMLWriter.render_tags(
                _render_tag_group(
                    key,
                    val,
                    object_type,
                    with_link=False,
                    label_type="label",
                    label_render_type="unspecified",
                    request=request,
                ),
                class_=["tagify", "label", "display"],
                readonly="true",
            )
            is_first_label = False

        group_html += "]"  # close group
        overall_html += HTMLWriter.render_div(group_html, class_="label_group")
        is_first_group = False

    return overall_html


def render_tag_groups(
    tag_groups: Mapping[TagGroupID, TagID], object_type: str, with_links: bool, *, request: Request
) -> HTML:
    return _render_tag_groups_or_labels(
        tag_groups,
        object_type,
        with_links,
        label_type="tag_group",
        label_sources={},
        request=request,
    )


def _render_tag_groups_or_labels(
    entries: Mapping[TagGroupID, TagID] | Labels,
    object_type: str,
    with_links: bool,
    label_type: str,
    label_sources: LabelSources,
    override_label_render_type: LabelRenderType | None = None,
    *,
    request: Request,
) -> HTML:
    elements = [
        _render_tag_group(
            tag_group_id_or_label_key,
            tag_id_or_label_value,
            object_type,
            with_links,
            label_type,
            (
                override_label_render_type
                if override_label_render_type
                else label_sources.get(tag_group_id_or_label_key, "unspecified")
            ),
            request=request,
        )
        for tag_group_id_or_label_key, tag_id_or_label_value in sorted(entries.items())
    ]
    return HTMLWriter.render_tags(
        HTML.without_escaping(" ").join(elements),
        class_=["tagify", label_type, "display"],
        readonly="true",
    )


def _render_tag_group(
    tag_group_id_or_label_key: TagGroupID | str,
    tag_id_or_label_value: TagID | str,
    object_type: str,
    with_link: bool,
    label_type: str,
    label_render_type: LabelRenderType,
    *,
    request: Request,
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
        class_=["tagify--noAnim", label_render_type],
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


def render_community_upgrade_button() -> None:
    html.icon_button(
        url="https://checkmk.com/pricing?services=3000?utm_source=checkmk_product&utm_medium=referral&utm_campaign=commercial_editions_link",
        title=_("Upgrade to Checkmk Enterprise or Checkmk Ultimate to use this feature"),
        icon=StaticIcon(IconNames.upgrade),
        target="_blank",
        cssclass="upgrade",
    )
