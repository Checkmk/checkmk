#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Realizes the popup action menu for hosts/services in views"""

from livestatus import livestatus_lql

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.servicename import ServiceName

from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.painter.v0.helpers import replace_action_url_macros, transform_action_url
from cmk.gui.type_defs import Row

from .painter import get_icons, IconEntry, IconObjectType, iconpainter_columns, LegacyIconEntry


def ajax_popup_action_menu(config: Config) -> None:
    site = SiteId(request.get_ascii_input_mandatory("site"))
    host = request.get_validated_type_input_mandatory(HostName, "host")
    svcdesc = request.get_str_input("service")
    what: IconObjectType = "service" if svcdesc else "host"

    display_options.load_from_html(request, html)

    row = _query_action_data(what, host, site, svcdesc)
    icons = get_icons(what, row, toplevel=False)

    html.open_ul()
    for icon in icons:
        if isinstance(icon, LegacyIconEntry):
            html.open_li()
            html.write_text_permissive(icon.code)
            html.close_li()
        elif isinstance(icon, IconEntry):
            html.open_li()
            if icon.url_spec:
                url, target_frame = transform_action_url(icon.url_spec)
                url = replace_action_url_macros(url, what, row)
                onclick = None
                if url.startswith("onclick:"):
                    onclick = url[8:]
                    url = "javascript:void(0);"
                html.open_a(href=url, target=target_frame, onclick=onclick)

            html.icon(icon.icon_name)
            if icon.title:
                html.write_text_permissive(icon.title)
            else:
                html.write_text_permissive(_("No title"))
            if icon.url_spec:
                html.close_a()
            html.close_li()
    html.close_ul()


def _query_action_data(
    what: IconObjectType, host: HostName, site: SiteId, svcdesc: ServiceName | None
) -> Row:
    # Now fetch the needed data from livestatus
    columns = list(iconpainter_columns(what, toplevel=False))
    try:
        columns.remove("site")
    except KeyError:
        pass

    query = livestatus_lql([host], columns, svcdesc)

    with sites.prepend_site(), sites.only_sites(site):
        row = sites.live().query_row(query)

    return dict(zip(["site"] + columns, row))
