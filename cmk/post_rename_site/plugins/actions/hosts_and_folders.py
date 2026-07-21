#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from logging import Logger

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.config import load_config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.site_config import all_activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils import paths
from cmk.utils.global_ident_type import GlobalIdent


def update_hosts_and_folders(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """Update the Checkmk site attribute in folder and host config files

    - Explicitly configured `site` attributes are updated
    - `site` host_tags entries in the hosts.mk files are updated
    """
    # Loading and saving folders and hosts relies on the host attribute and folder
    # validator registries being populated. The registration only runs once per
    # process; the call is a no-op in case another rename action already did it.
    main_modules.register(edition(paths.omd_root))

    config = load_config()
    # This runs unattended on the command line; act as the superuser explicitly instead
    # of swapping the request scoped session user via SuperUserContext.
    acting_user = LoggedInSuperUser()
    pending_changes = PendingChanges(
        activation_sites=all_activation_sites(config.sites),
        local_site=omd_site(),
        acting_user=acting_user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=config.wato_use_git),
            index_update_change_hook,
        ),
    )
    for folder in make_folder_tree(config).all_folders().values():
        # 1. Update explicitly set site in folders
        if folder.attributes.get("site") == old_site_id:
            logger.debug(
                "Folder %(folder_path)s: Update explicitly set site",
                {"folder_path": folder.alias_path()},
            )
            folder.attributes["site"] = new_site_id

        for host in folder.hosts().values():
            # 2. Update explicitly set site in hosts
            if host.attributes.get("site") == old_site_id:
                logger.debug(
                    "Host %(host_name)s: Update explicitly set site", {"host_name": host.name()}
                )
                host.attributes["site"] = new_site_id

            # 3. Update the locked_by attribute in hosts
            if locked_by := _update_locked_by(old_site_id, new_site_id, host.locked_by()):
                logger.debug(
                    "Host %(host_name)s: Update dynamic site configuration",
                    {"host_name": host.name()},
                )
                host.update_attributes(
                    {"locked_by": locked_by},
                    pprint_value=config.wato_pprint_config,
                    pending_changes=pending_changes,
                    acting_user=acting_user,
                )

        # Always rewrite the host config: The host_tags need to be updated, even in case there is no
        # site_id explicitly set. Just to be sure everything is fine we also rewrite the folder
        # config
        logger.debug("Folder %(folder_path)s: Saving config", {"folder_path": folder.alias_path()})
        folder.save(pprint_value=config.wato_pprint_config, acting_user=acting_user)


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


rename_action_hosts_and_folders = RenameAction(
    name=Name("hosts_and_folders"),
    title=Title("Hosts and folders"),
    sort_index=SortIndex(15),
    run=update_hosts_and_folders,
)
