#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Setup shared by the in-process tests of the monitoring REST endpoints."""

import copy
from collections.abc import Iterable

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole


def roles_without_permission(
    config: Config, role: str, permission: str
) -> dict[str, BuiltInUserRole | CustomUserRole]:
    """The configured roles, with ``permission`` withheld from ``role``."""
    roles = copy.deepcopy(config.roles)
    roles[role]["permissions"] = {**roles[role].get("permissions", {}), permission: False}
    return roles


def site_configurations(site_ids: Iterable[str]) -> dict[SiteId, SiteConfiguration]:
    """Connected sites the request schema accepts, each answering on the mock connection."""
    return {
        SiteId(site_id): SiteConfiguration(
            id=SiteId(site_id),
            alias=site_id,
            socket=("local", None),
            disable_wato=True,
            disabled=False,
            insecure=False,
            url_prefix=f"/{site_id}/",
            multisiteurl="",
            persist=False,
            replicate_ec=False,
            replicate_mkps=False,
            replication=None,
            timeout=5,
            user_login=True,
            proxy=None,
            user_attribute_sync_connections="all",
            status_host=None,
            message_broker_port=5672,
            is_trusted=False,
        )
        for site_id in site_ids
    }
