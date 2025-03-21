#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import Sequence

from livestatus import SiteId

from cmk.utils.i18n import _

from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def update_hosts_and_folders(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """Update the Checkmk site attribute in folder and host config files

    - Explicitly configured `site` attributes are updated
    - `site` host_tags entries in the hosts.mk files are updated
    """
    for folder in folder_tree().all_folders().values():
        # 1. Update explicitly set site in folders
        if folder.attributes.get("site") == old_site_id:
            logger.debug("Folder %s: Update explicitly set site", folder.alias_path())
            folder.attributes["site"] = new_site_id

        for host in folder.hosts().values():
            # 2. Update explicitly set site in hosts
            if host.attributes.get("site") == old_site_id:
                logger.debug("Host %s: Update explicitly set site", host.name())
                host.attributes["site"] = new_site_id

            # 3. Update the locked_by attribute in hosts
            if locked_by := _update_locked_by(
                old_site_id, new_site_id, host.attributes.get("locked_by")
            ):
                logger.debug("Host %s: Update dynamic site configuration", host.name())
                host.update_attributes({"locked_by": locked_by})

        # Always rewrite the host config: The host_tags need to be updated, even in case there is no
        # site_id explicitly set. Just to be sure everything is fine we also rewrite the folder
        # config
        logger.debug("Folder %s: Saving config", folder.alias_path())
        folder.save()
        folder.save_hosts()


def _update_locked_by(
    old_site_id: SiteId, new_site_id: SiteId, locked_by: Sequence[str] | None
) -> Sequence[str] | None:
    if not locked_by:
        return None

    if locked_by[0] != old_site_id:
        return None

    return (new_site_id, *locked_by[1:])


rename_action_registry.register(
    RenameAction(
        name="hosts_and_folders",
        title=_("Hosts and folders"),
        sort_index=15,
        handler=update_hosts_and_folders,
    )
)
