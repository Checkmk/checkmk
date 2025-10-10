#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from livestatus import SiteId

import cmk.utils.render
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import Labels
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.rulesets.ruleset_matcher import LabelSources
from cmk.utils.tags import TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import urlencode
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


def paint_host_list(site: SiteId, hosts: list[HostName]) -> CellSpec:
    return "", HTML(
        ", ".join(
            get_host_list_links(
                site,
                [str(host) for host in hosts],
            )
        )
    )


def format_plugin_output(output: str, row: Row) -> HTML:
    return cmk.gui.view_utils.format_plugin_output(
        output,
        must_escape=not active_config.sites[row["site"]].get("is_trusted", False),
        row=row,
        shall_escape=active_config.escape_plugin_output,
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
