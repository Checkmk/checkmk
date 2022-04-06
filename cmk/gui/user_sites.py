#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import List, Optional, Tuple

from livestatus import SiteConfigurations, SiteId

from cmk.utils.site import omd_site

from cmk.gui.logged_in import user as global_user
from cmk.gui.site_config import configured_sites, site_is_local


def sorted_sites() -> List[Tuple[SiteId, str]]:
    return sorted(
        [(site_id, s["alias"]) for site_id, s in global_user.authorized_sites().items()],
        key=lambda k: k[1].lower(),
    )


def get_configured_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(global_user.authorized_sites(unfiltered_sites=configured_sites()))


def site_attribute_default_value() -> Optional[SiteId]:
    site_id = omd_site()
    authorized_site_ids = global_user.authorized_sites(unfiltered_sites=configured_sites()).keys()
    if site_id in authorized_site_ids:
        return site_id
    return None


def site_choices(site_configs: SiteConfigurations) -> List[Tuple[SiteId, str]]:
    """Compute the choices to be used e.g. in dropdowns from a SiteConfigurations collection"""
    choices = []
    for site_id, site_spec in site_configs.items():
        title = site_id
        if site_spec.get("alias"):
            title += " - " + site_spec["alias"]

        choices.append((site_id, title))

    return sorted(choices, key=lambda s: s[1])


def get_event_console_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(
        SiteConfigurations(
            {
                site_id: site
                for site_id, site in global_user.authorized_sites(
                    unfiltered_sites=configured_sites()
                ).items()
                if site_is_local(site_id) or site.get("replicate_ec", False)
            }
        )
    )


def get_activation_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(activation_sites())


def activation_sites() -> SiteConfigurations:
    """Returns sites that are affected by WATO changes

    These sites are shown on activation page and get change entries
    added during WATO changes."""
    return SiteConfigurations(
        {
            site_id: site
            for site_id, site in global_user.authorized_sites(
                unfiltered_sites=configured_sites()
            ).items()
            if site_is_local(site_id) or site.get("replication")
        }
    )
