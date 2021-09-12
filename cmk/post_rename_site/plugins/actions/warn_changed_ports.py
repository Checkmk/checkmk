#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from livestatus import SiteId

from cmk.utils.i18n import _
from cmk.utils.log.console import warning

from cmk.post_rename_site.main import logger
from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def warn_about_network_ports(old_site_id: SiteId, new_site_id: SiteId) -> None:
    if not Path("/omd/sites", old_site_id).exists():
        return  # Site was not copied

    logger.info("")
    warning(
        "Network port configuration may need your attention\n\n"
        "It seems like you copied an existing site. In case you plan to use both on the same "
        "system, you may have to review the network port configuration of your sites. Two sites"
        "with the same configuration may cause network port conflicts."
        "For example if you enabled livestatus to listen via TCP or enabled the Event Console "
        "to listen for incoming Syslog messages or SNMP traps, you may have to update the "
        "configuration in one of the sites to resolve the conflicts.\n"
    )


rename_action_registry.register(
    RenameAction(
        name="warn_about_network_ports",
        title=_("Warn about new network ports"),
        sort_index=955,
        handler=warn_about_network_ports,
    )
)
