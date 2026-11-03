#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Replication of the event status from a master EC to a slave EC"""

# mypy: disable-error-code="explicit-any"

import logging
import os
import shlex
import signal
import socket
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import FrameType
from typing import Any, Literal
from unittest.mock import Mock

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ec.config import Config, ScriptAction, ScriptActionConfig
from cmk.ec.helpers import ECLock
from cmk.ec.history import History
from cmk.ec.main import (
    default_slave_status_master,
    default_slave_status_sync,
    EventServer,
    EventStatus,
    get_state_from_master,
    load_configuration,
    load_master_config,
    MKSignalException,
    PackedEventStatus,
    reload_configuration,
    replication_pull,
    save_master_config,
    save_slave_status,
    SlaveStatus,
    StatusServer,
    update_slave_status,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.query import MKClientError

from .helpers import (
    activate_config,
    FakeConnection,
    MASTER,
    new_event,
    new_message,
    new_rule,
    query_status_server,
    replication_slave_config,
)

_NOW = 1_750_000_000.0

type _FetchMasterState = Callable[[Config, SlaveStatus], dict[str, object]]
type _Pull = Callable[[Config, _FetchMasterState], None]


@pytest.fixture(name="slave_status")
def fixture_slave_status() -> SlaveStatus:
    """The EC of these tests is a syncing replication slave if its configuration says so"""
    return default_slave_status_sync()


@pytest.fixture(name="pull")
def fixture_pull(
    settings: ec.Settings,
    lock_configuration: ECLock,
    perfcounters: Perfcounters,
    event_status: EventStatus,
    event_server: EventServer,
    slave_status: SlaveStatus,
) -> _Pull:
    def pull(config: Config, fetch_master_state: _FetchMasterState) -> None:
        with time_machine.travel(_NOW, tick=False):
            replication_pull(
                settings,
                config,
                lock_configuration,
                perfcounters,
                event_status,
                event_server,
                slave_status,
                logging.getLogger("cmk.mkeventd"),
                fetch_master_state=fetch_master_state,
            )

    return pull


def _master(
    *events: ec.Event,
    rule_packs: Sequence[ec.ECRulePack] | None = None,
    actions: Sequence[ec.Action] = (),
    rule_stats: Mapping[str, int] | None = None,
) -> _FetchMasterState:
    """A reachable master with events and hits and, given its rule packs, a changed configuration"""

    def fetch_master_state(_config: Config, _slave_status: SlaveStatus) -> dict[str, object]:
        state: dict[str, object] = {
            "status": PackedEventStatus(
                next_event_id=len(events) + 1,
                # Like those of any master, the events have IDs.
                events=[
                    event | ec.Event(id=event_id) for event_id, event in enumerate(events, start=1)
                ],
                rule_stats=dict(rule_stats or {}),
                interval_starts={},
            )
        }
        if rule_packs is not None:
            state |= {"rules": [], "rule_packs": rule_packs, "actions": list(actions)}
        return state

    return fetch_master_state


def _unreachable_master(_config: Config, _slave_status: SlaveStatus) -> dict[str, object]:
    raise Exception("Master not responding")


def _replicate(status_server: StatusServer, last_update: str) -> dict[str, Any]:
    response = query_status_server(status_server, f"REPLICATE {last_update}").get_response()
    assert isinstance(response, dict)
    return response


def test_replication_slave_without_saved_status_starts_syncing(
    settings: ec.Settings, config: Config
) -> None:
    slave_status = default_slave_status_master()

    update_slave_status(slave_status, settings, replication_slave_config(config))

    assert slave_status["mode"] == "sync"


def test_former_replication_slave_becomes_master(settings: ec.Settings, config: Config) -> None:
    slave_status = default_slave_status_sync()

    update_slave_status(slave_status, settings, config)

    assert slave_status["mode"] == "master"


def test_former_replication_slave_forgets_its_saved_status(
    settings: ec.Settings, config: Config
) -> None:
    settings.paths.slave_status_file.value.write_text(repr(default_slave_status_sync()))

    update_slave_status(default_slave_status_sync(), settings, config)

    assert not settings.paths.slave_status_file.value.exists()


def test_former_replication_slave_uses_its_own_rules(
    settings: ec.Settings, slave_status: SlaveStatus
) -> None:
    own_rule_pack = ec.default_rule_pack([new_rule({"id": "own"})])
    activate_config(settings, f"rule_packs = [{own_rule_pack!r}]\n")
    # Saved when this EC was a replication slave
    master_rule_pack = ec.default_rule_pack([new_rule({"id": "from_master"})])
    save_master_config(
        settings, MASTER, {"rules": [], "rule_packs": [master_rule_pack], "actions": []}
    )

    config = load_configuration(settings, logging.getLogger("test_ec_replication"), slave_status)

    assert config["rule_packs"] == [own_rule_pack]


def test_flushing_a_replication_slave_keeps_its_replication_status(
    settings: ec.Settings,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    status_server: StatusServer,
) -> None:
    slave_config = replication_slave_config(config)
    status_server.reload_configuration(slave_config, history)
    save_master_config(settings, MASTER, {"rules": [], "rule_packs": [], "actions": []})
    takeover_status = SlaveStatus(
        last_master_down=1234.0, last_sync=1000.0, mode="takeover", success=False
    )
    slave_status.update(takeover_status)
    save_slave_status(settings, slave_status)

    query_status_server(status_server, "COMMAND FLUSH")

    reloaded_slave_status = default_slave_status_master()
    update_slave_status(reloaded_slave_status, settings, slave_config)
    assert (slave_status, reloaded_slave_status) == (takeover_status, takeover_status)


def test_flushing_a_replication_slave_keeps_the_rules_of_its_master(
    settings: ec.Settings, config: Config, history: History, status_server: StatusServer
) -> None:
    slave_config = replication_slave_config(config)
    status_server.reload_configuration(slave_config, history)
    master_rule_pack = ec.default_rule_pack([new_rule({"id": "from_master"})])
    save_master_config(
        settings, MASTER, {"rules": [], "rule_packs": [master_rule_pack], "actions": []}
    )

    query_status_server(status_server, "COMMAND FLUSH")

    reloaded_config = slave_config.copy()
    load_master_config(settings, reloaded_config, logging.getLogger("cmk.mkeventd"))
    assert reloaded_config["rule_packs"] == [master_rule_pack]


def test_replication_slave_keeps_its_status_if_the_saved_one_is_unreadable(
    settings: ec.Settings, config: Config
) -> None:
    takeover_status = SlaveStatus(
        last_master_down=1234.0, last_sync=1000.0, mode="takeover", success=False
    )
    slave_status = takeover_status.copy()
    settings.paths.slave_status_file.value.write_text("")  # e.g. after running out of disk space

    update_slave_status(slave_status, settings, replication_slave_config(config))

    assert slave_status == takeover_status


def test_replication_slave_of_another_master_syncs_completely_with_it(
    settings: ec.Settings, slave_status: SlaveStatus
) -> None:
    replication = ec.Replication(connect_timeout=10, interval=60, master=("other-master", 6558))
    activate_config(settings, f"replication = {replication!r}\n")
    # The slave synced with its previous master, which sent its rules.
    save_master_config(settings, MASTER, {"rules": [], "rule_packs": [], "actions": []})
    save_slave_status(
        settings, SlaveStatus(last_master_down=None, last_sync=1000.0, mode="sync", success=True)
    )

    load_configuration(settings, logging.getLogger("test_ec_replication"), slave_status)

    assert slave_status == default_slave_status_sync()


def test_replication_slave_of_another_master_does_not_use_the_rules_of_the_previous_one(
    settings: ec.Settings, slave_status: SlaveStatus
) -> None:
    own_rule_pack = ec.default_rule_pack([new_rule({"id": "own"})])
    replication = ec.Replication(connect_timeout=10, interval=60, master=("other-master", 6558))
    activate_config(settings, f"rule_packs = [{own_rule_pack!r}]\nreplication = {replication!r}\n")
    previous_rule_pack = ec.default_rule_pack([new_rule({"id": "from_previous_master"})])
    save_master_config(
        settings, MASTER, {"rules": [], "rule_packs": [previous_rule_pack], "actions": []}
    )

    config = load_configuration(settings, logging.getLogger("test_ec_replication"), slave_status)

    assert config["rule_packs"] == [own_rule_pack]


@pytest.mark.parametrize(
    "broken_master_config",
    [
        pytest.param("None", id="not a dict"),
        pytest.param("{[1]: 2}", id="unparsable dict"),
    ],
)
def test_replication_slave_starts_despite_a_broken_saved_master_configuration(
    settings: ec.Settings, slave_status: SlaveStatus, broken_master_config: str
) -> None:
    replication = ec.Replication(connect_timeout=10, interval=60, master=MASTER)
    activate_config(settings, f"replication = {replication!r}\n")
    takeover_status = SlaveStatus(
        last_master_down=1234.0, last_sync=1000.0, mode="takeover", success=False
    )
    save_slave_status(settings, takeover_status)
    # Nobody validates files edited by hand.
    settings.paths.master_config_file.value.write_text(broken_master_config)

    load_configuration(settings, logging.getLogger("test_ec_replication"), slave_status)

    assert slave_status == takeover_status


@pytest.mark.parametrize(
    "saved_master_config",
    [
        pytest.param(None, id="missing"),
        pytest.param("", id="empty, e.g. after an interrupted save"),
    ],
)
def test_replication_slave_without_a_saved_master_configuration_logs_no_error(
    settings: ec.Settings,
    slave_status: SlaveStatus,
    caplog: pytest.LogCaptureFixture,
    saved_master_config: str | None,
) -> None:
    replication = ec.Replication(connect_timeout=10, interval=60, master=MASTER)
    activate_config(settings, f"replication = {replication!r}\n")
    if saved_master_config is not None:
        settings.paths.master_config_file.value.write_text(saved_master_config)

    load_configuration(settings, logging.getLogger("test_ec_replication"), slave_status)

    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_master_replicates_its_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    response = _replicate(status_server, "0")

    assert [event["text"] for event in response["status"]["events"]] == ["disk full"]


_STATUS_AND_CONFIGURATION = {"status", "rules", "rule_packs", "actions"}


@pytest.mark.parametrize(
    "seconds_from_reload_to_last_update, expected_keys",
    [
        pytest.param(-1, _STATUS_AND_CONFIGURATION, id="outdated slave"),
        pytest.param(0, _STATUS_AND_CONFIGURATION, id="slave synced in the second of the reload"),
        pytest.param(1, {"status"}, id="up-to-date slave"),
    ],
)
def test_master_replicates_its_configuration_only_if_it_changed(
    config: Config,
    status_server: StatusServer,
    seconds_from_reload_to_last_update: int,
    expected_keys: set[str],
) -> None:
    response = _replicate(
        status_server, str(config["last_reload"] + seconds_from_reload_to_last_update)
    )

    assert set(response) == expected_keys


def test_master_replicates_its_configuration_to_a_slave_which_synced_during_the_reload(
    settings: ec.Settings,
    logger: logging.Logger,
    history: History,
    event_status: EventStatus,
    status_server: StatusServer,
    slave_status: SlaveStatus,
) -> None:
    # Unlike SQLite, recording the history in files leaves nothing open after the test.
    activate_config(settings, 'archive_mode = "file"\n')
    with time_machine.travel(_NOW, tick=False) as traveller:
        # Reloading takes a while, e.g. to compile many rules, and a slave syncs after a second.
        slow_event_server = Mock(spec=EventServer)
        slow_event_server.reload_configuration.side_effect = lambda *_args: traveller.shift(2)
        reload_configuration(
            settings,
            logger,
            history,
            event_status,
            slow_event_server,
            status_server,
            slave_status,
        )

    response = _replicate(status_server, str(int(_NOW) + 1))

    assert set(response) == _STATUS_AND_CONFIGURATION


def test_master_refuses_invalid_replication_requests(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Invalid arguments to command REPLICATE"):
        _replicate(status_server, "yesterday")


def test_syncing_slave_gets_the_events_of_its_master(
    event_status: EventStatus, config: Config, pull: _Pull
) -> None:
    pull(replication_slave_config(config), _master(new_event(ec.Event(text="disk full"))))

    assert [event["text"] for event in event_status.events()] == ["disk full"]


def test_syncing_slave_gets_the_rules_of_its_master(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    pull: _Pull,
) -> None:
    slave_config = replication_slave_config(config)
    event_server.reload_configuration(slave_config, history)
    master_rule_pack = ec.default_rule_pack([new_rule({"id": "from_master"})])
    pull(slave_config, _master(rule_packs=[master_rule_pack]))
    # Only a slave which took over processes messages.
    slave_status["mode"] = "takeover"

    event_server.process_potential_event_instrumented([new_message(ec.Event(text="disk full"))])

    assert [event["rule_id"] for event in event_status.events()] == ["from_master"]


def test_syncing_slave_passes_the_rules_of_its_master_on_right_away(
    status_server: StatusServer, config: Config, history: History, pull: _Pull
) -> None:
    # The slave reloaded its configuration a minute ago, a slave of its own synced since then.
    slave_config = replication_slave_config(config) | {"last_reload": int(_NOW) - 60}
    status_server.reload_configuration(slave_config, history)
    master_rule_pack = ec.default_rule_pack([new_rule({"id": "from_master"})])
    pull(slave_config, _master(rule_packs=[master_rule_pack]))

    response = _replicate(status_server, str(int(_NOW) - 30))

    assert response.get("rule_packs") == [master_rule_pack]


def test_rule_hits_a_syncing_slave_got_from_its_master_are_restored_after_a_restart(
    settings: ec.Settings,
    perfcounters: Perfcounters,
    history: History,
    core_connection: FakeConnection,
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    pull: _Pull,
) -> None:
    # The master changed the rule, which started its hits over there.
    slave_config = replication_slave_config(config) | {
        "rule_packs": [ec.default_rule_pack([new_rule({"id": "disk"})])]
    }
    event_server.reload_configuration(slave_config, history)
    master_rule_pack = ec.default_rule_pack([new_rule({"id": "disk", "description": "edited"})])
    pull(slave_config, _master(rule_packs=[master_rule_pack], rule_stats={"disk": 1}))
    event_status.save_status()
    # Like the slave's configuration after syncing, the restarted one has the rules of the master.
    restarted_event_status = EventStatus(
        settings,
        slave_config,
        perfcounters,
        history,
        logging.getLogger("cmk.mkeventd.EventStatus"),
        core_connection,
    )

    restarted_event_status.load_status(event_server)

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_slave_which_took_over_executes_the_actions_of_its_master(
    tmp_path: Path,
    event_status: EventStatus,
    status_server: StatusServer,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    pull: _Pull,
) -> None:
    slave_config = replication_slave_config(config)
    status_server.reload_configuration(slave_config, history)
    # Only the master knows this action.
    ticket_file = tmp_path / "ticket"
    master_action = ScriptAction(
        id="ticket",
        title="Open a ticket",
        hidden=False,
        disabled=False,
        action=(
            "script",
            ScriptActionConfig(script=f'printf %s "$CMK_TEXT" > {shlex.quote(str(ticket_file))}'),
        ),
    )
    pull(slave_config, _master(rule_packs=[], actions=[master_action]))
    slave_status["mode"] = "takeover"
    event_status.new_event(new_event(ec.Event(text="disk full")))

    query_status_server(status_server, "COMMAND ACTION;1;harry;ticket")

    assert ticket_file.read_text() == "disk full"


def test_slave_which_took_over_counts_the_events_of_its_master_towards_its_limits(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    pull: _Pull,
) -> None:
    slave_config = replication_slave_config(config) | {
        "event_limit": config["event_limit"] | {"by_host": ec.EventLimit(action="stop", limit=1)},
        "rule_packs": [ec.default_rule_pack([new_rule({})])],
    }
    event_server.reload_configuration(slave_config, history)
    pull(slave_config, _master(new_event(ec.Event(text="from master"))))
    slave_status["mode"] = "takeover"

    event_server.process_potential_event_instrumented([new_message(ec.Event(text="disk full"))])

    assert [event["text"] for event in event_status.events()] == ["from master"]


@pytest.mark.parametrize(
    "mode, expected_phases",
    [
        pytest.param("sync", ["delayed"], id="syncing"),
        pytest.param("takeover", ["open"], id="taken over"),
    ],
)
def test_slave_does_the_housekeeping_of_the_events_only_after_taking_over(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    pull: _Pull,
    mode: Literal["sync", "takeover"],
    expected_phases: list[str],
) -> None:
    slave_config = replication_slave_config(config)
    event_server.reload_configuration(slave_config, history)
    # The master delayed this event, and the delay is over now.
    pull(slave_config, _master(new_event(ec.Event(phase="delayed", delay_until=_NOW))))
    slave_status["mode"] = mode

    with time_machine.travel(_NOW, tick=False):
        event_server.do_housekeeping()

    assert [event["phase"] for event in event_status.events()] == expected_phases


def test_syncing_slave_still_expires_its_own_history(
    settings: ec.Settings, event_server: EventServer, config: Config, history: History
) -> None:
    event_server.reload_configuration(replication_slave_config(config), history)
    expired_log_file = settings.paths.history_dir.value / "expired.log"
    expired_log_file.parent.mkdir(parents=True, exist_ok=True)
    expired_log_file.touch()
    os.utime(expired_log_file, (0, 0))

    event_server.do_housekeeping()

    assert not expired_log_file.exists()


def test_successful_sync_is_recorded(
    slave_status: SlaveStatus, config: Config, pull: _Pull
) -> None:
    pull(replication_slave_config(config), _master())

    assert (slave_status["success"], slave_status["last_sync"]) == (True, _NOW)


def test_failed_sync_is_recorded(slave_status: SlaveStatus, config: Config, pull: _Pull) -> None:
    pull(replication_slave_config(config), _unreachable_master)

    assert (slave_status["success"], slave_status["last_master_down"]) == (False, _NOW)


def test_signal_while_syncing_is_passed_on(config: Config, pull: _Pull) -> None:
    def fetch_master_state(_config: Config, _slave_status: SlaveStatus) -> dict[str, object]:
        raise MKSignalException(signal.SIGTERM)

    with pytest.raises(MKSignalException):
        pull(replication_slave_config(config), fetch_master_state)


def test_signal_while_waiting_for_the_master_is_passed_on(
    config: Config, slave_status: SlaveStatus
) -> None:
    def signal_handler(signum: int, _stack_frame: FrameType | None) -> None:
        raise MKSignalException(signum)

    with socket.socket() as master:  # accepts connections, but never answers
        master.bind(("127.0.0.1", 0))
        master.listen()
        replication = ec.Replication(connect_timeout=10, interval=60, master=master.getsockname())
        previous_handler = signal.signal(signal.SIGALRM, signal_handler)
        signal.setitimer(signal.ITIMER_REAL, 0.1)
        try:
            with pytest.raises(MKSignalException):
                get_state_from_master(config | {"replication": replication}, slave_status)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)


def test_replication_status_survives_a_restart(
    settings: ec.Settings, slave_status: SlaveStatus, config: Config, pull: _Pull
) -> None:
    slave_config = replication_slave_config(config)
    pull(slave_config, _master())
    restarted_slave_status = default_slave_status_master()

    update_slave_status(restarted_slave_status, settings, slave_config)

    assert restarted_slave_status == slave_status


@pytest.mark.parametrize(
    "last_sync, expected_mode",
    [
        pytest.param(0, "sync", id="never synced"),
        pytest.param(_NOW - 59, "sync", id="within takeover period"),
        pytest.param(_NOW - 60, "takeover", id="after takeover period"),
    ],
)
def test_slave_takes_over_when_its_master_is_unreachable_for_too_long(
    slave_status: SlaveStatus, config: Config, pull: _Pull, last_sync: float, expected_mode: str
) -> None:
    slave_status["last_sync"] = last_sync

    pull(replication_slave_config(config, takeover=60), _unreachable_master)

    assert slave_status["mode"] == expected_mode


@pytest.mark.parametrize(
    "fallback, last_master_down, expected_mode",
    [
        pytest.param(None, None, "takeover", id="without fallback"),
        pytest.param(60, None, "sync", id="master reachable for the first time"),
        pytest.param(60, _NOW - 59, "sync", id="within fallback period"),
        pytest.param(60, _NOW - 60, "takeover", id="after fallback period"),
    ],
)
def test_slave_falls_back_to_syncing_when_its_master_is_reachable_again(
    slave_status: SlaveStatus,
    config: Config,
    pull: _Pull,
    fallback: int | None,
    last_master_down: float | None,
    expected_mode: str,
) -> None:
    slave_status["mode"] = "takeover"
    slave_status["last_master_down"] = last_master_down

    pull(replication_slave_config(config, takeover=60, fallback=fallback), _master())

    assert slave_status["mode"] == expected_mode
