#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.relay.lib.site_client import SiteRelaysClient


async def get_site_relays_client() -> SiteRelaysClient:
    config = get_config()
    return SiteRelaysClient.from_site(
        site_url=config.rest_api_url,
        internal_site_url=config.internal_rest_api_url,
        site_name=config.site_name,
    )
