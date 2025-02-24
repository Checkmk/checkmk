#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import threading
from collections.abc import Iterator
from unittest import mock

import pytest

import cmk.utils.paths

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.helpers import ECLock
from cmk.ec.history_file import FileHistory
from cmk.ec.history_mongo import MongoDBHistory
from cmk.ec.history_sqlite import SQLiteHistory, SQLiteSettings
from cmk.ec.main import (
    create_history,
    default_slave_status_master,
    EventServer,
    EventStatus,
    make_config,
    SlaveStatus,
    StatusServer,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.settings import create_settings


@pytest.fixture(name="settings")
def fixture_settings() -> ec.Settings:
    return create_settings("1.2.3i45", cmk.utils.paths.omd_root, ["mkeventd"])


@pytest.fixture(name="lock_configuration")
def fixture_lock_configuration() -> ECLock:
    return ECLock(logging.getLogger("cmk.mkeventd.configuration"))


@pytest.fixture(name="slave_status")
def fixture_slave_status() -> SlaveStatus:
    return default_slave_status_master()


@pytest.fixture(name="config")
def fixture_config() -> Config:
    return make_config(ec.default_config())


@pytest.fixture(name="history")
def fixture_history(settings: ec.Settings, config: Config) -> FileHistory:
    history = create_history(
        settings,
        config | {"archive_mode": "file"},
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )
    assert isinstance(history, FileHistory)
    return history


@pytest.fixture(name="history_mongo")
def fixture_history_mongo(settings: ec.Settings, config: Config) -> Iterator[MongoDBHistory]:
    """history_mongo with connection config file mocked"""

    connection_string = os.getenv("MONGODB_CONNECTION_STRING") or ""

    connection_opts = (
        (connection_string,) if connection_string.startswith("mongodb://") else ("localhost", 27017)
    )

    with mock.patch(
        "cmk.ec.history_mongo._mongodb_local_connection_opts",
        mock.Mock(return_value=connection_opts),
    ):
        history = create_history(
            settings,
            config | {"archive_mode": "mongodb"},
            logging.getLogger("cmk.mkeventd"),
            StatusTableEvents.columns,
            StatusTableHistory.columns,
        )
        assert isinstance(history, MongoDBHistory)
        yield history
        history.flush()


@pytest.fixture(name="history_sqlite")
def fixture_history_sqlite(settings: ec.Settings, config: Config) -> Iterator[SQLiteHistory]:
    """history_sqlite with history file path set to :memory:"""

    history = SQLiteHistory(
        SQLiteSettings.from_settings(settings, database=":memory:"),
        config | {"archive_mode": "sqlite"},
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )

    yield history

    history.flush()


@pytest.fixture(name="perfcounters")
def fixture_perfcounters() -> Perfcounters:
    return Perfcounters(logging.getLogger("cmk.mkeventd.lock.perfcounters"))


@pytest.fixture(name="event_status")
def fixture_event_status(
    settings: ec.Settings, config: Config, perfcounters: Perfcounters, history: FileHistory
) -> EventStatus:
    return EventStatus(
        settings, config, perfcounters, history, logging.getLogger("cmk.mkeventd.EventStatus")
    )


@pytest.fixture(name="event_server")
def fixture_event_server(
    settings: ec.Settings,
    config: Config,
    slave_status: SlaveStatus,
    perfcounters: Perfcounters,
    lock_configuration: ECLock,
    history: FileHistory,
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
    settings: ec.Settings,
    config: Config,
    slave_status: SlaveStatus,
    perfcounters: Perfcounters,
    lock_configuration: ECLock,
    history: FileHistory,
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
        threading.Event(),
    )
