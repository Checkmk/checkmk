#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class CleanUpSiteAttributes(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        site_mgmt = site_management_registry["site_management"]
        configured_sites = site_mgmt.load_sites()

        for site_id, site_spec in configured_sites.items():
            site_spec.setdefault("alias", str(site_id))
            site_spec.setdefault("socket", ("local", None))
            site_spec.setdefault("url_prefix", "../")  # relative URL from /check_mk/
            site_spec["id"] = site_id
            site_spec.setdefault("message_broker_port", 5672)
            site_spec.setdefault("url_prefix", f"/{site_id}/")
            site_spec.setdefault("user_sync", "all")
            site_spec.setdefault("proxy", None)
            site_spec.setdefault("replicate_mkps", False)
            site_spec.setdefault("status_host", None)

        site_mgmt.save_sites(
            configured_sites,
            activate=False,
            pprint_value=active_config.wato_pprint_config,
        )


update_action_registry.register(
    CleanUpSiteAttributes(
        name="clean_up_site_attributes",
        title="Clean up site connections",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )
)
