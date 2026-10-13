#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.config import get_default_config, make_base_config
from cmk.base.configlib.loaded_config import BaseConfig


def test_base_config_defaults_match_default_config() -> None:
    assert BaseConfig() == make_base_config(get_default_config())
