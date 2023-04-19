#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

from livestatus import LivestatusOutputFormat, LivestatusResponse, SiteId

from cmk.utils.paths import default_config_dir

from cmk.gui import sites
from cmk.gui.i18n import _

from cmk.bi.compiler import BICompiler
from cmk.bi.computer import BIComputer
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.lib import SitesCallback


class BIManager:
    def __init__(self) -> None:
        sites_callback = SitesCallback(all_sites_with_id_and_online, bi_livestatus_query, _)
        self.compiler = BICompiler(self.bi_configuration_file(), sites_callback)
        self.compiler.load_compiled_aggregations()
        self.status_fetcher = BIStatusFetcher(sites_callback)
        self.computer = BIComputer(self.compiler.compiled_aggregations, self.status_fetcher)

    @classmethod
    def bi_configuration_file(cls) -> str:
        return str(Path(default_config_dir) / "multisite.d" / "wato" / "bi_config.bi")


def all_sites_with_id_and_online() -> list[tuple[SiteId, bool]]:
    return [
        (site_id, site_status["state"] == "online")
        for site_id, site_status in sites.states().items()
    ]


def bi_livestatus_query(
    query: str,
    only_sites: list[SiteId] | None = None,
    output_format: LivestatusOutputFormat = LivestatusOutputFormat.PYTHON,
    fetch_full_data: bool = False,
) -> LivestatusResponse:

    with sites.output_format(output_format), sites.only_sites(only_sites), sites.prepend_site():
        try:
            auth_domain = "bi_fetch_full_data" if fetch_full_data else "bi"
            sites.live().set_auth_domain(auth_domain)
            return sites.live().query(query)
        finally:
            sites.live().set_auth_domain("read")
