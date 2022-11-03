#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import pathlib

import pytest

import cmk.utils.paths

import cmk.ec.export as ec
from cmk.ec.config import Config, ConfigFromWATO
from cmk.ec.history import History
from cmk.ec.main import StatusTableEvents, StatusTableHistory
from cmk.ec.settings import Settings


@pytest.fixture(name="settings", scope="function")
def fixture_settings() -> Settings:
    return ec.settings(
        "1.2.3i45",
        cmk.utils.paths.omd_root,
        pathlib.Path(cmk.utils.paths.default_config_dir),
        ["mkeventd"],
    )


@pytest.fixture(name="history", scope="function")
def fixture_history(settings: Settings, config: Config) -> History:
    return History(
        settings,
        config,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )


@pytest.fixture(name="config", scope="function")
def fixture_config() -> ConfigFromWATO:
    return ec.default_config()
