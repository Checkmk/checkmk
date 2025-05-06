#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from logging import Logger

from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId

from cmk.utils.global_ident_type import GlobalIdent

from cmk.gui.config import active_config
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
            if locked_by := _update_locked_by(old_site_id, new_site_id, host.locked_by()):
                logger.debug("Host %s: Update dynamic site configuration", host.name())
                host.update_attributes(
                    {"locked_by": locked_by}, pprint_value=active_config.wato_pprint_config
                )

        # Always rewrite the host config: The host_tags need to be updated, even in case there is no
        # site_id explicitly set. Just to be sure everything is fine we also rewrite the folder
        # config
        logger.debug("Folder %s: Saving config", folder.alias_path())
        folder.save(pprint_value=active_config.wato_pprint_config)


def _update_locked_by(
    old_site_id: SiteId, new_site_id: SiteId, locked_by: GlobalIdent | None
) -> Sequence[str] | None:
    if not locked_by:
        return None

    if locked_by["site_id"] != old_site_id:
        return None

    return (
        new_site_id,
        locked_by["program_id"],
        locked_by["instance_id"],
    )


rename_action_registry.register(
    RenameAction(
        name="hosts_and_folders",
        title=_("Hosts and folders"),
        sort_index=15,
        handler=update_hosts_and_folders,
    )
)
