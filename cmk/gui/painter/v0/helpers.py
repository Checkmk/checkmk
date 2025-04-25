#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils.render
from cmk.utils.labels import Labels, LabelSources
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.tags import TagGroupID, TagID

from cmk.gui import http
from cmk.gui.config import active_config
from cmk.gui.display_options import DisplayOptions
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.tag_rendering import HTMLTagAttributeValue
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ColumnName, HTTPVariables, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri_contextless, urlencode
from cmk.gui.view_utils import CellSpec, get_host_list_links


def transform_action_url(url_spec: tuple[str, str] | str) -> tuple[str, str | None]:
    if isinstance(url_spec, tuple):
        return url_spec
    return (url_spec, None)


def replace_action_url_macros(url: str, what: str, row: Row) -> str:
    macros = {
        "HOSTNAME": row["host_name"],
        "HOSTADDRESS": row["host_address"],
        "USER_ID": user.id,
    }
    if what == "service":
        macros.update(
            {
                "SERVICEDESC": row["service_description"],
            }
        )
    return replace_macros_in_str(
        url,
        {
            k_mod: v_mod
            for k_orig, v_orig in macros.items()
            for k_mod, v_mod in (
                (f"${k_orig}$", v_orig),
                (f"${k_orig}_URL_ENCODED$", urlencode(v_orig)),
            )
        },
    )


def render_cache_info(what: str, row: Row) -> str:
    cached_at = row["service_cached_at"]
    cache_interval = row["service_cache_interval"]
    cache_age = time.time() - cached_at

    text = _("Cache generated %s ago, cache interval: %s") % (
        cmk.utils.render.approx_age(cache_age),
        cmk.utils.render.approx_age(cache_interval),
    )

    if cache_interval:
        percentage = 100.0 * cache_age / cache_interval
        text += _(", elapsed cache lifespan: %s") % cmk.utils.render.percent(percentage)

    return text


def paint_host_list(site: SiteId, hosts: list[HostName], *, request: Request) -> CellSpec:
    return "", HTML.without_escaping(", ").join(
        get_host_list_links(
            site,
            [str(host) for host in hosts],
            request=request,
        )
    )


def format_plugin_output(output: str, *, request: Request, row: Row) -> HTML:
    return cmk.gui.view_utils.format_plugin_output(
        output, request=request, row=row, shall_escape=active_config.escape_plugin_output
    )


def format_labels_for_csv_export(labels: Labels) -> str:
    return ", ".join(f"{k}:{v}" for k, v in labels.items())


def get_tag_groups(row: Row, what: str) -> Mapping[TagGroupID, TagID]:
    # Sites with old versions that don't have the tag groups column return
    # None for this field. Convert this to the default value
    groups = row.get("%s_tags" % what, {}) or {}
    assert isinstance(groups, dict)
    return groups


def get_label_sources(row: Row, what: str) -> LabelSources:
    # Sites with old versions that don't have the label_sources column return
    # None for this field. Convert this to the default value
    sources = row.get("%s_label_sources" % what, {}) or {}
    assert isinstance(sources, dict)
    return sources


def paint_nagiosflag(row: Row, field: ColumnName, bold_if_nonzero: bool) -> CellSpec:
    nonzero = row[field] != 0
    return (
        "badflag" if nonzero == bold_if_nonzero else "goodflag",
        HTMLWriter.render_span(_("yes") if nonzero else _("no")),
    )


class RenderLink:
    def __init__(
        self,
        request: http.Request,
        response: http.Response,
        display_options: DisplayOptions,
    ):
        self.request = request
        self.response = response
        self.display_options = display_options

    def link_direct(
        self,
        url: str,
        *,
        html_text: HTML | str | None = None,
        **attributes: HTMLTagAttributeValue,
    ) -> HTML:
        if self.display_options.disabled(self.display_options.I):
            return HTML.empty()

        return HTMLWriter.render_a(html_text, href=url, **attributes)

    def link_from_filename(
        self,
        filename: str,
        *,
        html_text: str | None = None,
        query_args: HTTPVariables | None = None,
        mobile_filename: str | None = None,
    ) -> HTML:
        """Return a fully rendered <a href...>...</a> tag."""
        _query_args: HTTPVariables = []
        if options := self.request.var("display_options"):
            _query_args.append(("display_options", options))

        if query_args is not None:
            _query_args.extend(query_args)

        url = makeuri_contextless(
            self.request,
            _query_args,
            filename=self.get_filename(filename=filename, mobile_filename=mobile_filename),
        )
        return self.link_direct(url, html_text=html_text)

    def get_filename(self, *, filename: str, mobile_filename: str | None = None) -> str:
        if mobile_filename is None:
            return filename
        return mobile_filename if is_mobile(self.request, self.response) else filename
