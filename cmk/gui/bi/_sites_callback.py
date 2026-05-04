#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import LivestatusResponse, Query

from cmk.bi.lib import SitesCallback
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.i18n import _


def create_default_sites_callback() -> SitesCallback:
    return SitesCallback(
        all_sites_with_id_and_online=_all_sites_with_id_and_online,
        query=_bi_livestatus_query,
        translate=_,
    )


def _all_sites_with_id_and_online() -> list[tuple[SiteId, bool]]:
    return [
        (site_id, site_status["state"] == "online")
        for site_id, site_status in sites.states().items()
    ]


def _bi_livestatus_query(
    query: Query,
    only_sites: list[SiteId] | None = None,
    fetch_full_data: bool = False,
) -> LivestatusResponse:
    with sites.only_sites(only_sites), sites.prepend_site():
        try:
            auth_domain = "bi_fetch_full_data" if fetch_full_data else "bi"
            sites.live().set_auth_domain(auth_domain)
            return sites.live().query(query)
        finally:
            sites.live().set_auth_domain("read")
