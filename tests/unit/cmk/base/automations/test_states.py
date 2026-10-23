#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import fields
from pathlib import Path

from cmk.base.automations.states import BaseConfigState
from tests.testlib.unit.empty_config import EMPTY_CONFIG


def test_base_config_state_picks_the_base_configuration() -> None:
    raw_config = {f.name: getattr(EMPTY_CONFIG, f.name) for f in fields(EMPTY_CONFIG)} | {
        "FOLDER_PATH": None,  # read by load_raw_config(), but no base configuration
    }

    assert BaseConfigState(Path("/old"), raw_config).loaded_config == EMPTY_CONFIG
