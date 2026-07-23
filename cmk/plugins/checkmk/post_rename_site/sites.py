#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.config import load_config
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.sites import site_management_registry
from cmk.post_rename_site.internal import (
    Name,
    RenameAction,
    SortIndex,
    Title,
)
from cmk.utils import paths


def update_site_config(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """Update the Checkmk GUI site configuration

    This mainly updates the sites.mk, but also triggers changes on the following files when calling
    save_sites().

    - etc/check_mk/liveproxyd.mk (Commercial editions only)
    - etc/check_mk/conf.d/distributed_wato.mk
    - etc/check_mk/dcd.d/wato/distributed.mk
    - etc/nagvis/conf.d/cmk_backends.ini.php
    """
    # The site management registry is populated by the GUI plug-in registration. The
    # registration only runs once per process; the call is a no-op in case another
    # rename action already did it.
    main_modules.register(edition(paths.omd_root))

    changed = False
    site_mgmt = site_management_registry["site_management"]
    all_sites = site_mgmt.load_sites()

    if old_site_id in all_sites:
        changed = True

        # 1. Transform entry in all sites
        logger.debug("Rename site configuration")
        site_spec = all_sites[new_site_id] = all_sites.pop(old_site_id)

        # 2. Update the sites URL prefix
        site_spec["url_prefix"] = site_spec["url_prefix"].replace(
            f"/{old_site_id}/", f"/{new_site_id}/"
        )

        # 3. Update the configuration connection
        site_spec["multisiteurl"] = site_spec["multisiteurl"].replace(
            f"/{old_site_id}/", f"/{new_site_id}/"
        )

        # 4. Update the "id" attribute
        site_spec["id"] = new_site_id

    # Iterate all sites and check for status host entries refering to the renamed site
    for this_site_id, site_cfg in all_sites.items():
        status_host = site_cfg.get("status_host")
        if status_host and status_host[0] == old_site_id:
            logger.debug("Update status host of site %(site_id)s", {"site_id": this_site_id})
            changed = True
            site_cfg["status_host"] = (new_site_id, status_host[1])

    if changed:
        config = load_config()
        site_mgmt.save_sites(
            make_folder_tree(config),
            all_sites,
            activate=True,
            pprint_value=config.wato_pprint_config,
            liveproxyd_enabled=config.liveproxyd_enabled,
            use_git=config.wato_use_git,
            acting_user_id=None,
        )


rename_action_sites = RenameAction(
    name=Name("sites"),
    title=Title("Distributed monitoring configuration"),
    sort_index=SortIndex(10),
    run=update_site_config,
)
