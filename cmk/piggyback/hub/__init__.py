#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from ._config import ConfigType as PiggybackHubConfigType
from ._config import HostLocations as HostLocations
from ._config import PiggybackHubConfig as PiggybackHubConfig
from ._config import publish_one_shot_locations as publish_one_shot_locations
from ._config import publish_persisted_locations as publish_persisted_locations
from ._config import save_config as save_piggyback_hub_config
from ._main import main as main

__all__ = [
    "save_piggyback_hub_config",
    "PiggybackHubConfigType",
]
