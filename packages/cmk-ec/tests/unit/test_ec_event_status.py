#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Keeping the status of the events, also across restarts of the EC"""

import ast
import logging
import pprint
from collections.abc import Mapping, Sequence
from typing import Protocol

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config, ExpectInterval
from cmk.ec.history import History
from cmk.ec.main import EventServer, EventStatus
from cmk.ec.perfcounters import Perfcounters

from .helpers import FakeConnection, new_event, new_host, new_rule


class _Restart(Protocol):
    def __call__(self, restarted_config: Config | None = None) -> EventStatus: ...


@pytest.fixture(name="restart")
def fixture_restart(
    settings: ec.Settings,
    config: Config,
    perfcounters: Perfcounters,
    history: History,
    core_connection: FakeConnection,
    event_server: EventServer,
) -> _Restart:
    """Returns the event status of a restarted EC, i.e. the loaded status saved before

    By default, the restarted EC has the same configuration as before."""

    def restart(restarted_config: Config | None = None) -> EventStatus:
        event_status = EventStatus(
            settings,
            config if restarted_config is None else restarted_config,
            perfcounters,
            history,
            logging.getLogger("cmk.mkeventd.EventStatus"),
            core_connection,
        )
        event_status.load_status(event_server)
        return event_status

    return restart


def _save_status_of_old_version(
    settings: ec.Settings, events: Sequence[object], rule_stats: Mapping[str, int] | None = None
) -> None:
    settings.paths.status_file.value.write_text(
        repr(
            {
                "next_event_id": len(events) + 1,
                "events": events,
                "rule_stats": dict(rule_stats or {}),
            }
        )
    )


def _with_rules(config: Config, *rules: ec.Rule) -> Config:
    return config | {"rule_packs": [ec.default_rule_pack(list(rules))]}


def test_saved_events_are_restored_after_a_restart(
    event_status: EventStatus, restart: _Restart
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))
    event_status.save_status()

    restarted_event_status = restart()

    assert [event["text"] for event in restarted_event_status.events()] == ["disk full"]


def test_event_ids_continue_after_a_restart(event_status: EventStatus, restart: _Restart) -> None:
    event_status.new_event(new_event(ec.Event(text="before restart")))
    event_status.save_status()
    restarted_event_status = restart()

    restarted_event_status.new_event(new_event(ec.Event(text="after restart")))

    assert [event["id"] for event in restarted_event_status.events()] == [1, 2]


def test_rule_hits_are_restored_after_a_restart(
    event_status: EventStatus, restart: _Restart
) -> None:
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)
    event_status.save_status()

    restarted_event_status = restart()

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_rule_hits_of_rules_changed_meanwhile_start_over_after_a_restart(
    config: Config, restart: _Restart
) -> None:
    # E.g. activating changes while the EC is stopped changes the rules without reloading them.
    event_status = restart(
        _with_rules(config, new_rule({"id": "changed"}), new_rule({"id": "unchanged"}))
    )
    event_status.count_rule_match("changed", rule_digests=event_status.rule_digests)
    event_status.count_rule_match("unchanged", rule_digests=event_status.rule_digests)
    event_status.save_status()

    restarted_event_status = restart(
        _with_rules(
            config,
            new_rule({"id": "changed", "description": "edited"}),
            new_rule({"id": "unchanged"}),
        )
    )

    assert list(restarted_event_status.get_rule_stats()) == [("unchanged", 1)]


def test_rule_hits_of_rules_saved_in_another_key_order_are_restored_after_a_restart(
    config: Config, restart: _Restart
) -> None:
    rule = new_rule({"id": "disk"})
    event_status = restart(_with_rules(config, rule))
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)
    event_status.save_status()
    # E.g. activating changes with pretty printed rules sorts their keys.
    pretty_printed_rule: ec.Rule = ast.literal_eval(pprint.pformat(rule))

    restarted_event_status = restart(_with_rules(config, pretty_printed_rule))

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_rule_hits_of_rules_with_keys_of_different_types_are_restored_after_a_restart(
    config: Config, restart: _Restart
) -> None:
    # Nobody validates rules written by hand, e.g. their keys may have types Python can't sort.
    patterns = ast.literal_eval("{2: 'CRIT', '1': 'WARN'}")
    rule = new_rule({"id": "disk", "state": ("text_pattern", patterns)})
    event_status = restart(_with_rules(config, rule))
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)
    event_status.save_status()

    restarted_event_status = restart(_with_rules(config, rule))

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_rule_hits_of_rules_with_sets_are_restored_after_a_restart(
    config: Config, restart: _Restart
) -> None:
    # Rules may hold sets, e.g. of sites. Equal sets may list their elements in different orders,
    # e.g. sets of strings in another process, and these sets of numbers in any process.
    rule = new_rule({"id": "disk", "match_site": ast.literal_eval("{9, 1}")})
    event_status = restart(_with_rules(config, rule))
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)
    event_status.save_status()

    restarted_event_status = restart(
        _with_rules(config, new_rule({"id": "disk", "match_site": ast.literal_eval("{1, 9}")}))
    )

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_rule_hits_are_restored_after_a_restart_with_disabled_rules_without_an_id(
    config: Config, restart: _Restart
) -> None:
    # Nobody validates rules written by hand, and the EC compiles no disabled ones.
    rule = new_rule({"id": "disk"})
    event_status = restart(_with_rules(config, rule))
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)
    event_status.save_status()
    disabled_rule = new_rule({"disabled": True})
    del disabled_rule["id"]

    restarted_event_status = restart(_with_rules(config, rule, disabled_rule))

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_rule_hits_saved_by_an_old_version_are_restored_after_a_restart(
    settings: ec.Settings, config: Config, restart: _Restart
) -> None:
    _save_status_of_old_version(settings, [], {"disk": 1})

    restarted_event_status = restart(_with_rules(config, new_rule({"id": "disk"})))

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_restored_events_count_towards_the_event_limits(
    event_status: EventStatus, restart: _Restart
) -> None:
    event = new_event(ec.Event(text="disk full"))
    event_status.new_event(event)
    event_status.save_status()

    restarted_event_status = restart()

    assert restarted_event_status.get_num_existing_events_by("by_host", event) == 1


def test_restored_events_of_old_versions_get_default_values(
    settings: ec.Settings, restart: _Restart
) -> None:
    _save_status_of_old_version(settings, [{"id": 1, "rule_id": "disk", "text": "disk full"}])

    restarted_event_status = restart()

    assert restarted_event_status.events() == [
        {
            "id": 1,
            "rule_id": "disk",
            "text": "disk full",
            "ipaddress": "",
            "host": "",
            "application": "",
            "pid": 0,
            "core_host": None,
            "host_in_downtime": False,
        }
    ]


def test_restored_events_of_old_versions_get_their_host_in_the_core(
    settings: ec.Settings, core_connection: FakeConnection, restart: _Restart
) -> None:
    core_connection.hosts = [new_host("fileserver")]
    _save_status_of_old_version(settings, [{"id": 1, "rule_id": "disk", "host": "FileServer"}])

    restarted_event_status = restart()

    assert [event["core_host"] for event in restarted_event_status.events()] == ["fileserver"]


def test_corrupt_saved_status_is_not_silently_discarded(
    settings: ec.Settings, restart: _Restart
) -> None:
    settings.paths.status_file.value.write_text("{")

    with pytest.raises(SyntaxError):
        restart()


# fmt: off
@pytest.mark.parametrize(
    "interval, timestamp, interval_count, expected",
    [
        pytest.param(3600,       7300.0,  0,   7200, id="start of the current hour"),
        pytest.param(3600,       7300.0,  1,  10800, id="start of the next hour"),
        pytest.param(3600,       7300.0, -1,   3600, id="start of the previous hour"),
        pytest.param((86400, 2), 10800.0, 0,   7200, id="start of the current day beginning at 2am"),
        pytest.param((86400, 2),  3600.0, 0, -79200, id="1am belongs to the previous day beginning at 2am"),
    ],
)
# fmt: on
def test_timestamps_are_clamped_to_the_start_of_their_interval(
    interval: ExpectInterval, timestamp: float, interval_count: int, expected: int
) -> None:
    assert EventStatus.clamp_timestamp_to_interval(interval, timestamp, interval_count) == expected
