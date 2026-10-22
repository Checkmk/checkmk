#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Commands sent to the status socket of the EC"""

import ast
import threading
from typing import Literal

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.history import History
from cmk.ec.main import EventStatus, SlaveStatus, StatusServer
from cmk.ec.query import MKClientError

from .helpers import new_event, query_status_server, replication_slave_config


def _command(status_server: StatusServer, command: str, *, allow_commands: bool = True) -> None:
    query_status_server(status_server, f"COMMAND {command}", allow_commands=allow_commands)


def _become_replication_slave(
    status_server: StatusServer, config: Config, history: History
) -> None:
    status_server.reload_configuration(replication_slave_config(config), history)


@pytest.mark.parametrize(
    "arguments, expected_rule_hits",
    [
        pytest.param(";disk", [("cpu", 1)], id="of one rule"),
        pytest.param("", [], id="of all rules"),
    ],
)
def test_resetting_counters_forgets_rule_hits(
    event_status: EventStatus,
    status_server: StatusServer,
    arguments: str,
    expected_rule_hits: list[tuple[str, int]],
) -> None:
    event_status.count_rule_match("cpu")
    event_status.count_rule_match("disk")

    _command(status_server, f"RESETCOUNTERS{arguments}")

    assert list(event_status.get_rule_stats()) == expected_rule_hits


def test_flushing_deletes_all_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "FLUSH")

    assert event_status.events() == []


def test_syncing_saves_the_events(
    settings: ec.Settings, event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "SYNC")

    saved_status = ast.literal_eval(settings.paths.status_file.value.read_text())
    assert [event["text"] for event in saved_status["events"]] == ["disk full"]


@pytest.mark.parametrize("mode", ["sync", "takeover"])
def test_replication_slave_switches_to_the_requested_mode(
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    status_server: StatusServer,
    mode: Literal["sync", "takeover"],
) -> None:
    _become_replication_slave(status_server, config, history)

    _command(status_server, f"SWITCHMODE;{mode}")

    assert slave_status["mode"] == mode


def test_replication_slave_refuses_to_switch_to_an_unknown_mode(
    config: Config, history: History, status_server: StatusServer
) -> None:
    _become_replication_slave(status_server, config, history)

    with pytest.raises(MKClientError, match="Invalid target mode master"):
        _command(status_server, "SWITCHMODE;master")


def test_master_refuses_to_switch_its_replication_mode(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="this is not a replication slave"):
        _command(status_server, "SWITCHMODE;sync")


def test_reloading_is_requested(
    status_server: StatusServer, reload_config_event: threading.Event
) -> None:
    _command(status_server, "RELOAD")

    assert reload_config_event.is_set()


def test_shutting_down_is_requested(
    status_server: StatusServer, terminate_main_event: threading.Event
) -> None:
    _command(status_server, "SHUTDOWN")

    assert terminate_main_event.is_set()


def test_created_message_is_passed_unchanged_to_the_event_pipe(
    settings: ec.Settings, status_server: StatusServer
) -> None:
    _command(status_server, "CREATE;disk /var full; 98% used")

    assert settings.paths.event_pipe.value.read_text() == "disk /var full; 98% used\n"


def test_user_executing_an_action_becomes_the_owner_of_the_event(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "ACTION;1;harry;@NOTIFY")

    assert [event["owner"] for event in event_status.events()] == ["harry"]


def test_undefined_action_is_refused(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    with pytest.raises(MKClientError, match="The action 'reboot' is not defined"):
        _command(status_server, "ACTION;1;harry;reboot")


def test_updating_a_nonexistent_event_is_refused(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="No event with id 1"):
        _command(status_server, "UPDATE;1;harry;1;my comment;my contact")


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("DELETE;1", id="DELETE"),
        pytest.param("DELETE_EVENTS_OF_HOST;fileserver", id="DELETE_EVENTS_OF_HOST"),
    ],
)
def test_deleting_without_a_user_is_refused(status_server: StatusServer, command: str) -> None:
    with pytest.raises(MKClientError, match="Wrong number of arguments"):
        _command(status_server, command)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("DELETE;1;harry", id="DELETE"),
        pytest.param("UPDATE;1;harry;1;my comment;my contact", id="UPDATE"),
        pytest.param("CHANGESTATE;1;harry;2", id="CHANGESTATE"),
        pytest.param("ACTION;1;harry;@NOTIFY", id="ACTION"),
    ],
)
def test_syncing_replication_slave_refuses_to_change_events(
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    status_server: StatusServer,
    command: str,
) -> None:
    _become_replication_slave(status_server, config, history)
    slave_status["mode"] = "sync"

    with pytest.raises(MKClientError, match="not allowed on a replication slave"):
        _command(status_server, command)


def test_commands_are_refused_where_disallowed(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Commands are disallowed via TCP"):
        _command(status_server, "RELOAD", allow_commands=False)


def test_unknown_command_is_refused(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Unknown command REBOOT"):
        _command(status_server, "REBOOT")
