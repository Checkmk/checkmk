#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

import fastapi

from cmk.agent_receiver.config import Config, get_config
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relays_repository(
    config: Annotated[Config, fastapi.Depends(get_config)],
) -> RelaysRepository:
    return RelaysRepository.from_site(config.site_url, config.site_name)
