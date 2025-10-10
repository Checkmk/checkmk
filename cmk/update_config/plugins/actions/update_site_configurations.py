#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from livestatus import SiteConfiguration

from cmk.gui.watolib.sites import SiteManagementFactory

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateSiteConfigurations(UpdateAction):
    """When introducing a new site config attribute we sometimes need to populate that on existing sites."""

    @override
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        changed = False
        site_mgmt = SiteManagementFactory().factory()
        all_sites = site_mgmt.load_sites()
        for site_id, site_cfg in all_sites.items():
            if self._set_is_trusted(site_cfg):
                logger.info("Trusting site %s", site_id)
                changed = True
        if changed:
            site_mgmt.save_sites(
                all_sites,
                activate=True,
            )

    @staticmethod
    def _set_is_trusted(site_config: SiteConfiguration) -> bool:
        """set the is_trusted attribute
        See Werk #17998:
        - We trust local sites
        - We trust sites with config sync enabled (if they are not customer sites (MSE))
        """
        if site_config.get("is_trusted") is None:
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
        sort_index=100,  # I am not aware of any constrains
    )
)
