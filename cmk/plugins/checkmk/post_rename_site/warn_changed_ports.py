#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

from cmk.ccc import tty
from cmk.ccc.site import SiteId
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils.log import console


def warn_about_network_ports(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    if not Path("/omd/sites", old_site_id).exists():
        return  # Site was not copied

    logger.info("")
    console.warning(
        tty.format_warning(
            "Network port configuration may need your attention\n\n"
            "It seems like you copied an existing site. In case you plan to use both on the same "
            "system, you may have to review the network port configuration of your sites. Two sites "
            "with the same configuration may cause network port conflicts. "
            "For example if you enabled livestatus to listen via TCP or enabled the Event Console "
            "to listen for incoming Syslog messages or SNMP traps, you may have to update the "
            "configuration in one of the sites to resolve the conflicts.\n"
            "If enabled, the same applies to the metric backend (Ultimate and Cloud editions only). "
            "Without changing the ports in one of the sites, port collisions will prevent one of "
            "the metric backends from starting, rendering your site dysfunctional.\n"
        )
    )


rename_action_warn_about_network_ports = RenameAction(
    name=Name("warn_about_network_ports"),
    title=Title("Warn about new network ports"),
    sort_index=SortIndex(955),
    run=warn_about_network_ports,
)
