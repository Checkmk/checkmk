#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteId

from cmk.utils.i18n import _

from cmk.gui.watolib.hosts_and_folders import Folder

from cmk.post_rename_site.main import logger
from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def update_hosts_and_folders(old_site_id: SiteId, new_site_id: SiteId) -> None:
    """Update the Checkmk site attribute in folder and host config files

    - Explicitly configured `site` attributes are updated
    - `site` host_tags entries in the hosts.mk files are updated
    """
    for folder in Folder.all_folders().values():
        # 1. Update explicitly set site in folders
        if folder.attribute("site") == old_site_id:
            logger.debug("Folder %s: Update explicitly set site", folder.alias_path())
            folder.set_attribute("site", new_site_id)

        # 2. Update explicitly set site in hosts
        for host in folder.hosts().values():
            if host.attribute("site") == old_site_id:
                logger.debug("Host %s: Update explicitly set site", host.name())
                host.set_attribute("site", new_site_id)

        # Always rewrite the host config: The host_tags need to be updated, even in case there is no
        # site_id explicitly set. Just to be sure everything is fine we also rewrite the folder
        # config
        logger.debug("Folder %s: Saving config", folder.alias_path())
        folder.save()
        folder.save_hosts()


rename_action_registry.register(
    RenameAction(
        name="hosts_and_folders",
        title=_("Hosts and folders"),
        sort_index=15,
        handler=update_hosts_and_folders,
    )
)
