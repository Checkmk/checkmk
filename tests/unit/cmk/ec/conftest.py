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
import cmk.ec.history
import cmk.ec.main


@pytest.fixture(name="settings", scope="function")
def fixture_settings():
    return ec.settings(
        "1.2.3i45",
        cmk.utils.paths.omd_root,
        pathlib.Path(cmk.utils.paths.default_config_dir),
        ["mkeventd"],
    )


@pytest.fixture(name="lock_configuration", scope="function")
def fixture_lock_configuration():
    return cmk.ec.main.ECLock(logging.getLogger("cmk.mkeventd.configuration"))


@pytest.fixture(name="slave_status", scope="function")
def fixture_slave_status():
    return cmk.ec.main.default_slave_status_master()


@pytest.fixture(name="config", scope="function")
def fixture_config():
    return ec.default_config()


@pytest.fixture(name="history", scope="function")
def fixture_history(settings, config):
    return cmk.ec.history.History(
        settings,
        config,
        logging.getLogger("cmk.mkeventd"),
        cmk.ec.main.StatusTableEvents.columns,
        cmk.ec.main.StatusTableHistory.columns,
    )


@pytest.fixture(name="perfcounters", scope="function")
def fixture_perfcounters():
    return cmk.ec.main.Perfcounters(logging.getLogger("cmk.mkeventd.lock.perfcounters"))


@pytest.fixture(name="event_status", scope="function")
def fixture_event_status(settings, config, perfcounters, history):
    return cmk.ec.main.EventStatus(
        settings, config, perfcounters, history, logging.getLogger("cmk.mkeventd.EventStatus")
    )


@pytest.fixture(name="event_server", scope="function")
def fixture_event_server(
    settings, config, slave_status, perfcounters, lock_configuration, history, event_status
):
    return cmk.ec.main.EventServer(
        logging.getLogger("cmk.mkeventd.EventServer"),
        settings,
        config,
        slave_status,
        perfcounters,
        lock_configuration,
        history,
        event_status,
        cmk.ec.main.StatusTableEvents.columns,
        False,
    )


@pytest.fixture(name="status_server", scope="function")
def fixture_status_server(
    settings,
    config,
    slave_status,
    perfcounters,
    lock_configuration,
    history,
    event_status,
    event_server,
):
    return cmk.ec.main.StatusServer(
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
