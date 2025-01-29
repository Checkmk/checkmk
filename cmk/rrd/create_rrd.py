#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.config_path import LATEST_CONFIG

from cmk.base import config  # pylint: disable=cmk-module-layer-violation
from cmk.base.config import CEEConfigCache  # pylint: disable=cmk-module-layer-violation
from cmk.base.utils import register_sigint_handler  # pylint: disable=cmk-module-layer-violation

from . import rrd  # pylint: disable=cmk-module-layer-violation


def create_rrd() -> None:
    def reload_config() -> CEEConfigCache:
        config.load_packed_config(LATEST_CONFIG)
        config_cache = config.get_config_cache()
        assert isinstance(config_cache, CEEConfigCache)
        return config_cache

    register_sigint_handler()
    rrd.create_rrds_keepalive(reload_config=reload_config)
