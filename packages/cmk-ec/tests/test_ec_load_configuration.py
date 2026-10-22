#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Loading and reloading the configuration of the EC"""

import logging
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

import cmk.ec.export as ec
from cmk.ec.config import EMailAction, EMailActionConfig
from cmk.ec.helpers import ECLock
from cmk.ec.history import History
from cmk.ec.main import (
    EventServer,
    EventStatus,
    load_configuration,
    reload_configuration,
    save_master_config,
    SlaveStatus,
    StatusServer,
)
from cmk.ec.settings import create_settings

from .helpers import activate_config, new_rule, process_message


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
