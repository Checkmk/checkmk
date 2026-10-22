#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Loading and reloading the configuration of the EC"""

import contextlib
import logging
import shlex
import sqlite3
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import override

import pytest

import cmk.ec.export as ec
from cmk.ccc.site import SiteId
from cmk.ec.config import Config, EMailAction, EMailActionConfig, ScriptAction, ScriptActionConfig
from cmk.ec.helpers import ECLock
from cmk.ec.history import History
from cmk.ec.log_level import VERBOSE
from cmk.ec.main import (
    create_history,
    default_slave_status_master,
    EventServer,
    EventStatus,
    load_configuration,
    reload_configuration,
    save_master_config,
    save_slave_status,
    SlaveStatus,
    StatusServer,
    StatusTableEvents,
    StatusTableHistory,
    update_slave_status,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.settings import create_settings, PortNumber

from .helpers import (
    activate_config,
    FakeConnection,
    new_event,
    new_rule,
    process_message,
    query_status_server,
    replication_slave_config,
)


@pytest.fixture(name="logger")
def fixture_logger(request: pytest.FixtureRequest) -> logging.Logger:
    """A logger of each test's own, so its configured levels don't affect other tests"""
    return logging.getLogger(f"test_ec_load_configuration.{request.node.name}")


type _Reload = Callable[[History], History]


@pytest.fixture(name="reload")
def fixture_reload(
    settings: ec.Settings,
    logger: logging.Logger,
    lock_configuration: ECLock,
    event_status: EventStatus,
    event_server: EventServer,
    status_server: StatusServer,
    slave_status: SlaveStatus,
) -> Iterator[_Reload]:
    """Reloads the activated configuration, replacing the given history of the EC by a new one

    The histories created by reloading are closed after the test.
    """
    new_histories: list[History] = []

    def reload(history: History) -> History:
        new_history = reload_configuration(
            settings,
            logger,
            lock_configuration,
            history,
            event_status,
            event_server,
            status_server,
            slave_status,
        )
        new_histories.append(new_history)
        return new_history

    yield reload
    for new_history in new_histories:
        new_history.close()


def test_actions_are_looked_up_by_their_id(
    settings: ec.Settings, logger: logging.Logger, slave_status: SlaveStatus
) -> None:
    action = EMailAction(
        id="mail",
        title="Send a mail",
        hidden=False,
        disabled=False,
        action=("email", EMailActionConfig(to="harry@example.com", subject="EC", body="$TEXT$")),
    )
    activate_config(settings, f"actions = [{action!r}]\n")

    config = load_configuration(settings, logger, slave_status)

    assert config["action"] == {"mail": action}


@pytest.mark.parametrize(
    "options, expected_level",
    [
        pytest.param([], logging.DEBUG, id="configured level"),
        pytest.param(["-v"], logging.NOTSET, id="verbosity from the command line"),
    ],
)
def test_configured_log_levels_apply_unless_the_verbosity_is_given(
    tmp_path: Path,
    logger: logging.Logger,
    slave_status: SlaveStatus,
    options: list[str],
    expected_level: int,
) -> None:
    settings = create_settings("1.2.3i45", tmp_path, ["mkeventd", *options])
    log_levels = {
        "cmk.mkeventd": logging.INFO,
        "cmk.mkeventd.EventServer": logging.DEBUG,
        "cmk.mkeventd.EventStatus": logging.INFO,
        "cmk.mkeventd.StatusServer": logging.INFO,
        "cmk.mkeventd.lock": logging.INFO,
    }
    activate_config(settings, f"log_level = {log_levels!r}\n")

    load_configuration(settings, logger, slave_status)

    assert logger.getChild("EventServer").level == expected_level


def test_replication_slave_restores_the_rules_of_its_master(
    settings: ec.Settings, logger: logging.Logger, slave_status: SlaveStatus
) -> None:
    replication = ec.Replication(connect_timeout=10, interval=60, master=("master", 6558))
    activate_config(settings, f"replication = {replication!r}\n")
    rule_pack = ec.default_rule_pack([new_rule({"id": "from_master"})])
    save_master_config(settings, {"rules": [], "rule_packs": [rule_pack], "actions": []})

    config = load_configuration(settings, logger, slave_status)

    assert config["rule_packs"] == [rule_pack]


def test_reloading_activates_the_changed_rules(
    settings: ec.Settings,
    history: History,
    event_status: EventStatus,
    event_server: EventServer,
    reload: _Reload,
) -> None:
    rule_pack = ec.default_rule_pack([new_rule({"id": "reloaded"})])
    activate_config(settings, f"rule_packs = [{rule_pack!r}]\n")

    reload(history)
    process_message(event_server, ec.Event(text="disk full"))

    assert [event["rule_id"] for event in event_status.events()] == ["reloaded"]


@pytest.fixture(name="sqlite_history")
def fixture_sqlite_history(
    settings: ec.Settings,
    config: Config,
    logger: logging.Logger,
    event_status: EventStatus,
    status_server: StatusServer,
) -> Iterator[History]:
    """Makes the EC record its history in SQLite, like it does by default"""
    sqlite_history = create_history(
        settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
    )
    event_status.reload_configuration(config, sqlite_history)
    status_server.reload_configuration(config, sqlite_history)
    yield sqlite_history
    with contextlib.suppress(sqlite3.ProgrammingError):  # if reloading closed it already
        sqlite_history.close()


def test_reloading_keeps_the_history(
    event_status: EventStatus,
    status_server: StatusServer,
    sqlite_history: History,
    reload: _Reload,
) -> None:
    event_status.new_event(new_event(ec.Event(text="before reloading")))
    # The new history opens the same database before the old one is closed.

    reload(sqlite_history)
    event_status.new_event(new_event(ec.Event(text="after reloading")))

    status_socket = query_status_server(status_server, "GET history\nColumns: event_text")
    assert status_socket.get_response() == [
        ["event_text"],
        ["after reloading"],
        ["before reloading"],
    ]


_RELOAD_TIMEOUT = 5.0  # seconds, a reload in a test usually takes milliseconds


class _ConcurrentReload(logging.Handler):
    """Reloads in another thread once a record gets logged

    The reload gets as far as it can then: Unless the logging thread holds the lock of the event
    status, nothing makes the reload wait for it, so the logging thread goes on only once the
    reload is complete. Fails if the reload doesn't end in time, instead of hanging until the test
    times out.
    """

    def __init__(self, event_status: EventStatus, reload: Callable[[], object]) -> None:
        super().__init__()
        self._event_status = event_status
        self._reload = reload
        self._error: Exception | None = None
        self._thread = threading.Thread(target=self._run)

    def _run(self) -> None:
        try:
            self._reload()
        except Exception as e:
            self._error = e

    @override
    def emit(self, record: logging.LogRecord) -> None:
        if self._thread.ident is None:  # reload only once
            self._thread.start()
            if not self._event_status.lock.locked():
                self._join()

    def finish(self) -> None:
        """Waits for the reload to end, failing if it didn't start or failed"""
        if self._thread.ident is None:
            raise AssertionError("nothing got logged")
        self._join()
        if self._error is not None:
            raise self._error

    def _join(self) -> None:
        self._thread.join(_RELOAD_TIMEOUT)
        if self._thread.is_alive():
            raise AssertionError(f"reload still running after {_RELOAD_TIMEOUT} seconds")


@contextlib.contextmanager
def _reloading_once_a_query_is_logged(
    event_status: EventStatus, reload: Callable[[], object]
) -> Iterator[None]:
    """Reloads in another thread once the status server logs a query, see _ConcurrentReload"""
    concurrent_reload = _ConcurrentReload(event_status, reload)
    status_server_logger = logging.getLogger("cmk.mkeventd.StatusServer")  # see its fixture
    previous_level = status_server_logger.level
    status_server_logger.setLevel(VERBOSE)  # the level for logging queries
    status_server_logger.addHandler(concurrent_reload)
    try:
        yield
    finally:
        status_server_logger.removeHandler(concurrent_reload)
        status_server_logger.setLevel(previous_level)
        concurrent_reload.finish()


def test_status_query_is_answered_despite_a_concurrent_reload(
    event_status: EventStatus,
    status_server: StatusServer,
    sqlite_history: History,
    reload: _Reload,
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    # The reload closes the history which the status server uses until then.
    with _reloading_once_a_query_is_logged(event_status, lambda: reload(sqlite_history)):
        status_socket = query_status_server(status_server, "GET history\nColumns: event_text")

    assert status_socket.get_response() == [["event_text"], ["disk full"]]


def _activate_config_with_unusable_history(settings: ec.Settings) -> None:
    """Activates a configuration with a history in MongoDB, which isn't set up"""
    activate_config(settings, 'archive_mode = "mongodb"\n')


# Without a MongoDB configuration, the EC can't create a history in MongoDB.
_MONGODB_NOT_SET_UP = FileNotFoundError


def test_failed_reload_keeps_the_previous_history_working(
    settings: ec.Settings,
    event_status: EventStatus,
    status_server: StatusServer,
    sqlite_history: History,
    reload: _Reload,
) -> None:
    _activate_config_with_unusable_history(settings)
    with pytest.raises(_MONGODB_NOT_SET_UP):
        reload(sqlite_history)

    event_status.new_event(new_event(ec.Event(text="disk full")))

    status_socket = query_status_server(status_server, "GET history\nColumns: event_text")
    assert status_socket.get_response() == [["event_text"], ["disk full"]]


def test_failed_reload_keeps_the_replication_status(
    settings: ec.Settings,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    reload: _Reload,
) -> None:
    takeover_status = SlaveStatus(
        last_master_down=1234.0, last_sync=1000.0, mode="takeover", success=False
    )
    slave_status.update(takeover_status)
    save_slave_status(settings, slave_status)
    # The configuration of this slave ends the replication, but the EC can't create its history.
    _activate_config_with_unusable_history(settings)

    with pytest.raises(_MONGODB_NOT_SET_UP):
        reload(history)

    saved_slave_status = default_slave_status_master()
    update_slave_status(saved_slave_status, settings, replication_slave_config(config))
    assert (slave_status, saved_slave_status) == (takeover_status, takeover_status)


def test_failed_reload_keeps_the_log_levels(
    settings: ec.Settings, logger: logging.Logger, history: History, reload: _Reload
) -> None:
    logger.setLevel(logging.WARNING)
    # The configuration logs on the default level "info", but the EC can't create its history.
    _activate_config_with_unusable_history(settings)

    with pytest.raises(_MONGODB_NOT_SET_UP):
        reload(history)

    assert logger.level == logging.WARNING


@pytest.fixture(name="snmp_trap_receiving_event_server")
def fixture_snmp_trap_receiving_event_server(
    settings: ec.Settings,
    config: Config,
    slave_status: SlaveStatus,
    perfcounters: Perfcounters,
    lock_configuration: ECLock,
    history: History,
    event_status: EventStatus,
    core_connection: FakeConnection,
) -> EventServer:
    """An event server receiving SNMP traps, without opening the socket for them"""
    return EventServer(
        logging.getLogger("cmk.mkeventd.EventServer"),
        settings._replace(options=settings.options._replace(snmptrap_udp=PortNumber(162))),
        config,
        slave_status,
        perfcounters,
        lock_configuration,
        history,
        event_status,
        StatusTableEvents.columns,
        core_connection,
        SiteId("hurz"),
        create_pipes_and_sockets=False,
    )


def test_failed_reload_keeps_the_previous_configuration(
    settings: ec.Settings,
    config: Config,
    logger: logging.Logger,
    lock_configuration: ECLock,
    history: History,
    event_status: EventStatus,
    snmp_trap_receiving_event_server: EventServer,
    status_server: StatusServer,
    slave_status: SlaveStatus,
) -> None:
    event_server = snmp_trap_receiving_event_server
    event_server.reload_configuration(config | {"log_messages": True}, history)
    # Nobody validates settings written by hand, e.g. the protocol of an SNMPv3 user.
    credential = {
        "description": "",
        "credentials": ("authNoPriv", "MD4", "harry", "secret"),
        "engine_ids": [],
    }
    activate_config(settings, f"snmp_credentials = [{credential!r}]\n")
    with pytest.raises(Exception, match="Invalid SNMP auth protocol: MD4"):
        reload_configuration(
            settings,
            logger,
            lock_configuration,
            history,
            event_status,
            event_server,
            status_server,
            slave_status,
        )

    process_message(event_server, ec.Event(text="disk full"))

    assert list(settings.paths.messages_dir.value.glob("*.log")) != []


def test_reload_completes_although_the_replication_status_cannot_be_updated(
    tmp_path: Path,
    settings: ec.Settings,
    history: History,
    event_status: EventStatus,
    status_server: StatusServer,
    reload: _Reload,
) -> None:
    # A directory in place of its file e.g. prevents an EC which isn't a replication slave from
    # removing the saved replication status.
    settings.paths.slave_status_file.value.mkdir()
    ticket_file = tmp_path / "ticket"
    action = ScriptAction(
        id="ticket",
        title="Open a ticket",
        hidden=False,
        disabled=False,
        action=(
            "script",
            ScriptActionConfig(script=f'printf %s "$CMK_TEXT" > {shlex.quote(str(ticket_file))}'),
        ),
    )
    activate_config(settings, f"actions = [{action!r}]\n")
    reload(history)
    event_status.new_event(new_event(ec.Event(text="disk full")))

    query_status_server(status_server, "COMMAND ACTION;1;harry;ticket")

    assert ticket_file.read_text() == "disk full"
