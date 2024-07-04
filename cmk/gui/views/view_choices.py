#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import data_source_registry
from cmk.gui.i18n import _, _u
from cmk.gui.type_defs import ViewSpec

from .store import get_permitted_views


def view_choices(only_with_hidden: bool = False, allow_empty: bool = True) -> list[tuple[str, str]]:
    choices = []
    if allow_empty:
        choices.append(("", ""))
    for name, view in get_permitted_views().items():
        if not only_with_hidden or view["single_infos"]:
            title = format_view_title(name, view)
            choices.append(("%s" % name, title))
    return choices


def format_view_title(name: str, view: ViewSpec) -> str:
    title_parts = []

    if view.get("mobile", False):
        title_parts.append(_("Mobile"))

    # Don't use the data source title because it does not really look good here
    datasource = data_source_registry[view["datasource"]]()
    infos = datasource.infos
    if "event" in infos:
        title_parts.append(_("Event Console"))
    elif view["datasource"].startswith("inv"):
        title_parts.append(_("HW/SW Inventory"))
    elif "aggr" in infos:
        title_parts.append(_("BI"))
    elif "log" in infos:
        title_parts.append(_("Log"))
    elif "service" in infos:
        title_parts.append(_("Services"))
    elif "host" in infos:
        title_parts.append(_("Hosts"))
    elif "hostgroup" in infos:
        title_parts.append(_("Host groups"))
    elif "servicegroup" in infos:
        title_parts.append(_("Service groups"))

    title_parts.append("{} ({})".format(_u(str(view["title"])), name))

    return " - ".join(map(str, title_parts))
