#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc.i18n import _
from cmk.ccc.site import SiteId

from cmk.gui.config import active_config
from cmk.gui.watolib.sites import site_management_registry

from cmk.post_rename_site.registry import rename_action_registry, RenameAction


def update_site_config(old_site_id: SiteId, new_site_id: SiteId, logger: Logger) -> None:
    """Update the Checkmk GUI site configuration

    This mainly updates the sites.mk, but also triggers changes on the following files when calling
    save_sites().

    - etc/check_mk/liveproxyd.mk (CEE/CME only)
    - etc/check_mk/conf.d/distributed_wato.mk
    - etc/check_mk/dcd.d/wato/distributed.mk
    - etc/nagvis/conf.d/cmk_backends.ini.php
    """
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

        # 1. Update the "id" attribute
        site_spec["id"] = new_site_id

    # Iterate all sites and check for status host entries refering to the renamed site
    for this_site_id, site_cfg in all_sites.items():
        status_host = site_cfg.get("status_host")
        if status_host and status_host[0] == old_site_id:
            logger.debug("Update status host of site %s", this_site_id)
            changed = True
            site_cfg["status_host"] = (new_site_id, status_host[1])

    if changed:
        site_mgmt.save_sites(
            all_sites,
            activate=True,
            pprint_value=active_config.wato_pprint_config,
        )


rename_action_registry.register(
    RenameAction(
        name="sites",
        title=_("Distributed monitoring configuration"),
        sort_index=10,
        handler=update_site_config,
    )
)
