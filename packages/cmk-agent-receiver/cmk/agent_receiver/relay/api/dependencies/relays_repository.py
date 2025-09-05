#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relays_repository() -> RelaysRepository:
    site_name = os.environ["OMD_SITE"]
    # Here as normal dependency injection does not work with the double app approach
    url = os.environ.get("SITE_URL", "http://localhost")
    return RelaysRepository.from_site(url, site_name)
