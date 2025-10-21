#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.agent_receiver.config import get_config
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relays_repository() -> RelaysRepository:
    config = get_config()
    return RelaysRepository.from_site(config.site_url, config.site_name, config.helper_config_dir)
