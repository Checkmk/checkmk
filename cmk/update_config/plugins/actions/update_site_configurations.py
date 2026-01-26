#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from livestatus import SiteConfiguration

from cmk.gui.config import active_config
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateSiteConfigurations(UpdateAction):
    """When introducing a new site config attribute we sometimes need to populate that on existing sites."""

    @override
    def __call__(self, logger: Logger) -> None:
        changed = False
        site_mgmt = site_management_registry["site_management"]
        all_sites = site_mgmt.load_sites()

        for site_id, site_cfg in all_sites.items():
            if self._set_is_trusted(site_cfg):
                logger.info("Trusting site %s", site_id)
                changed = True

        if changed:
            # Note: In a remote site this method would also reach the method
            # update_distributed_wato files - which is dangerous, because of the risk
            # of duplicate hosts. However, there is also a guard within this method
            # that prevents the creation of the distributed_wato files in remote sites.
            # Just rewrite the sites.mk and nothing else.
            site_mgmt.save_sites(
                all_sites,
                activate=False,
                pprint_value=active_config.wato_pprint_config,
            )

    @staticmethod
    def _set_is_trusted(site_config: SiteConfiguration) -> bool:
        """set the is_trusted attribute

        See Werk #17998:
        - We trust local sites
        - We trust sites with config sync enabled (if they are not customer sites (MSE))
        """

        # mypy trusts the typing, I'm not so confident
        if site_config.get("is_trusted") is None:  # type: ignore[comparison-overlap]
            site_config["is_trusted"] = site_config["socket"] == ("local", None) or (
                site_config["replication"] == "slave"
                and site_config.get("customer", "provider") == "provider"
            )
            return True
        return False


update_action_registry.register(
    UpdateSiteConfigurations(
        name="update_site_configurations",
        title="Updating site configurations",
        sort_index=100,  # Runs after distributed_wato.mk renaming step (migrate_distributed_wato)
        expiry_version=ExpiryVersion.CMK_300,
    )
)
