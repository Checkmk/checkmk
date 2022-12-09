#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import pathlib
import threading

import pytest

import cmk.utils.paths

import cmk.ec.export as ec
from cmk.ec.config import Config, ConfigFromWATO
from cmk.ec.history import History
from cmk.ec.main import (
    default_slave_status_master,
    ECLock,
    EventServer,
    EventStatus,
    Perfcounters,
    SlaveStatus,
    StatusServer,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.settings import Settings


@pytest.fixture(name="settings", scope="function")
def fixture_settings() -> Settings:
    return ec.settings(
        "1.2.3i45",
        cmk.utils.paths.omd_root,
        pathlib.Path(cmk.utils.paths.default_config_dir),
        ["mkeventd"],
    )


@pytest.fixture(name="lock_configuration")
def fixture_lock_configuration() -> ECLock:
    return ECLock(logging.getLogger("cmk.mkeventd.configuration"))


@pytest.fixture(name="slave_status")
def fixture_slave_status() -> SlaveStatus:
    return default_slave_status_master()


@pytest.fixture(name="config", scope="function")
def fixture_config() -> ConfigFromWATO:
    return ec.default_config()


@pytest.fixture(name="history", scope="function")
def fixture_history(settings: Settings, config: Config) -> History:
    return History(
        settings,
        config,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )


@pytest.fixture(name="perfcounters")
def fixture_perfcounters() -> Perfcounters:
    return Perfcounters(logging.getLogger("cmk.mkeventd.lock.perfcounters"))


@pytest.fixture(name="event_status")
def fixture_event_status(
    settings: Settings, config: Config, perfcounters: Perfcounters, history: History
) -> EventStatus:
    return EventStatus(
        settings, config, perfcounters, history, logging.getLogger("cmk.mkeventd.EventStatus")
    )


@pytest.fixture(name="event_server")
def fixture_event_server(
    settings: Settings,
    config: Config,
    slave_status: SlaveStatus,
    perfcounters: Perfcounters,
    lock_configuration: ECLock,
    history: History,
    event_status: EventStatus,
) -> EventServer:
    return EventServer(
        logging.getLogger("cmk.mkeventd.EventServer"),
        settings,
        config,
        slave_status,
        perfcounters,
        lock_configuration,
        history,
        event_status,
        StatusTableEvents.columns,
        False,
    )


@pytest.fixture(name="status_server")
def fixture_status_server(
    settings: Settings,
    config: Config,
    slave_status: SlaveStatus,
    perfcounters: Perfcounters,
    lock_configuration: ECLock,
    history: History,
    event_status: EventStatus,
    event_server: EventServer,
) -> StatusServer:
    return StatusServer(
        logging.getLogger("cmk.mkeventd.StatusServer"),
        settings,
        config,
        slave_status,
        perfcounters,
        lock_configuration,
        history,
        event_status,
        event_server,
        threading.Event(),
    )
