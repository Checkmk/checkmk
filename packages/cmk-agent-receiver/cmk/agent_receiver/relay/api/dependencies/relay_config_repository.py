#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.relay.lib.relay_config_repository import RelayConfigRepository


async def get_relay_config_repository() -> RelayConfigRepository:
    return RelayConfigRepository(helper_config_dir=get_config().helper_config_dir)
