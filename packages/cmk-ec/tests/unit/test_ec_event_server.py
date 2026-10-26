#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from typing import Literal

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config, MatchGroups
from cmk.ec.history import History
from cmk.ec.main import (
    create_history,
    EventServer,
    EventStatus,
    StatusTableEvents,
    StatusTableHistory,
)

from .helpers import new_event, new_rule, process_message


def _make_rule(state: ec.State) -> ec.Rule:
    return new_rule({"id": "patterns", "state": state})


@pytest.mark.parametrize(
    "state,priority,expected",
    [
        pytest.param(-1, ec.SyslogPriority(0), 2, id="set by syslog, prio 0"),
        pytest.param(-1, ec.SyslogPriority(1), 2, id="set by syslog, prio 1"),
        pytest.param(-1, ec.SyslogPriority(2), 2, id="set by syslog, prio 2"),
        pytest.param(-1, ec.SyslogPriority(3), 2, id="set by syslog, prio 3"),
        pytest.param(-1, ec.SyslogPriority(4), 1, id="set by syslog, prio 4"),
        pytest.param(-1, ec.SyslogPriority(5), 0, id="set by syslog, prio 5"),
        pytest.param(-1, ec.SyslogPriority(6), 0, id="set by syslog, prio 6"),
        pytest.param(-1, ec.SyslogPriority(7), 0, id="set by syslog, prio 7"),
        pytest.param(0, ec.SyslogPriority(0), 0, id="set to OK"),
        pytest.param(1, ec.SyslogPriority(0), 1, id="set to WARN"),
        pytest.param(2, ec.SyslogPriority(0), 2, id="set to CRIT"),
        pytest.param(3, ec.SyslogPriority(0), 3, id="set to UNKNOWN"),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm", "2": "HURZ"}),
            ec.SyslogPriority(0),
            2,
            id="set via text (CRIT)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm", "2": "foo"}),
            ec.SyslogPriority(0),
            1,
            id="set via text (WARN)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "foo", "2": "bar"}),
            ec.SyslogPriority(0),
            0,
            id="set via text (OK)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm"}),
            ec.SyslogPriority(0),
            1,
            id="set via text (OK, missing CRIT)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "2": "foo"}),
            ec.SyslogPriority(0),
            0,
            id="set via text (OK, missing WARN)",
        ),
    ],
)
def test_rewrite_event_state(
    event_server: EventServer, state: ec.State, priority: ec.SyslogPriority, expected: int
) -> None:
    rule = _make_rule(state)
    ec.compile_rule(rule)
    event = new_event(
        ec.Event(
            host=HostName("heute"),
            text='Und das Lamm schrie: "Hurz!"',
            core_host=HostName("heute"),
            priority=priority.value,
        )
    )
    assert "state" not in event

    event_server.rewrite_event(rule=rule, event=event, match_groups=MatchGroups())

    assert event["state"] == expected


def test_compiling_the_rules_keeps_the_rule_packs_for_replication_intact(
    event_server: EventServer,
) -> None:
    rule_packs = [ec.default_rule_pack([_make_rule(("text_pattern", {"2": "ERR.*"}))])]

    event_server.compile_rules(rule_packs)

    assert rule_packs == [ec.default_rule_pack([_make_rule(("text_pattern", {"2": "ERR.*"}))])]


def _reload_configuration(
    event_server: EventServer,
    settings: ec.Settings,
    config: Config,
    rule_packs: Sequence[ec.ECRulePack],
) -> None:
    # Unlike SQLite, recording the history in files leaves nothing open after the test.
    config_rule_packs = config | {"rule_packs": rule_packs, "archive_mode": "file"}
    history = create_history(
        settings,
        config_rule_packs,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )
    event_server.reload_configuration(config_rule_packs, history=history)


def test_rule_which_cannot_be_compiled_does_not_match(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    # The rule would match any message, only one of its state patterns is an invalid regex.
    rule = _make_rule(("text_pattern", {"2": "(("}))
    _reload_configuration(event_server, settings, config, [ec.default_rule_pack([rule])])

    process_message(event_server, ec.Event(text="Something happened"))

    assert event_status.events() == []


def _rule(
    rule_id: str, *, disabled: bool = False, drop: bool | Literal["skip_pack"] = False
) -> ec.Rule:
    """Returns a rule which matches any message"""
    rule = _make_rule(0)
    rule["id"] = rule_id
    rule["disabled"] = disabled
    rule["drop"] = drop
    return rule


def _rule_pack(pack_id: str, *rules: ec.Rule, disabled: bool = False) -> ec.ECRulePackSpec:
    return ec.ECRulePackSpec(id=pack_id, title=pack_id, disabled=disabled, rules=list(rules))


def _rule_ids_of_events(event_status: EventStatus) -> list[str | None]:
    return [event["rule_id"] for event in event_status.events()]


def test_disabled_rule_packs_and_rules_are_ignored(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [
        _rule_pack("disabled", _rule("in_disabled_pack"), disabled=True),
        _rule_pack("enabled", _rule("disabled", disabled=True), _rule("enabled")),
    ]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["enabled"]


def test_a_rule_which_skips_its_rule_pack_skips_its_other_rules(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [
        _rule_pack("skipped", _rule("skipping", drop="skip_pack"), _rule("skipped")),
        _rule_pack("next", _rule("next")),
    ]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["next"]


def test_a_rule_which_drops_the_message_stops_processing_it(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [_rule_pack("pack", _rule("dropping", drop=True), _rule("matching"))]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == []


def test_a_cancelling_match_cancels_the_events_of_the_rule(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule = _rule("disk")
    rule["match"] = "disk failed"
    rule["match_ok"] = "disk ok"
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", rule)])
    process_message(event_server, ec.Event(text="disk failed"))
    assert _rule_ids_of_events(event_status) == ["disk"]

    process_message(event_server, ec.Event(text="disk ok"))

    assert _rule_ids_of_events(event_status) == []


def test_a_host_name_which_cannot_be_translated_is_empty(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    # Nobody validates settings written by hand.
    config_with_translation = config | {"hostname_translation": {"regex": [("((", "x")]}}
    _reload_configuration(
        event_server, settings, config_with_translation, [_rule_pack("pack", _rule("matching"))]
    )

    process_message(event_server, ec.Event(text="Something happened"))

    assert [event["host"] for event in event_status.events()] == [""]


def test_message_cannot_break_the_housekeeping_by_setting_the_lifetime_of_its_event(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("matching"))])
    message = (
        b"<134>1 2026-10-23T10:00:00Z fileserver smartd - - "
        b'[Checkmk@18662 live_until="tomorrow"] disk full'
    )
    event_server.process_syslog_messages([message], None)

    event_server.do_housekeeping()

    assert [event["phase"] for event in event_status.events()] == ["open"]


_RULE_OPTIMIZER = [
    pytest.param(True, id="with rule optimizer"),
    pytest.param(False, id="without rule optimizer"),
]


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "priorities",
    [
        pytest.param((4, 0), id="descending range"),
        pytest.param((0, 4), id="ascending range"),
    ],
)
def test_rule_matches_messages_within_its_priority_range(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    priorities: tuple[int, int],
) -> None:
    rule = _rule("critical")
    rule["match_priority"] = priorities
    _reload_configuration(
        event_server, settings, config | {"rule_optimizer": rule_optimizer}, [_rule_pack("p", rule)]
    )

    process_message(event_server, ec.Event(text="Something happened", priority=2))

    assert _rule_ids_of_events(event_status) == ["critical"]


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "cancel_priorities",
    [
        pytest.param((7, 5), id="descending range"),
        pytest.param((5, 7), id="ascending range"),
    ],
)
def test_message_within_the_cancel_priority_range_cancels_the_event(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    cancel_priorities: tuple[int, int],
) -> None:
    rule = _rule("critical")
    rule["match_priority"] = (2, 0)
    rule["cancel_priority"] = cancel_priorities
    _reload_configuration(
        event_server, settings, config | {"rule_optimizer": rule_optimizer}, [_rule_pack("p", rule)]
    )
    process_message(event_server, ec.Event(text="Disk failed", priority=2))
    assert _rule_ids_of_events(event_status) == ["critical"]

    process_message(event_server, ec.Event(text="Disk OK", priority=6))

    assert _rule_ids_of_events(event_status) == []


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "priorities",
    [
        pytest.param((8, 0), id="descending range"),
        pytest.param((0, 8), id="ascending range"),
    ],
)
def test_rule_with_a_priority_beyond_debug_is_ignored(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    priorities: tuple[int, int],
) -> None:
    # Nobody validates rules written by hand.
    invalid_rule = _rule("invalid")
    invalid_rule["match_priority"] = priorities
    _reload_configuration(
        event_server,
        settings,
        config | {"rule_optimizer": rule_optimizer},
        [_rule_pack("p", invalid_rule, _rule("valid"))],
    )

    process_message(event_server, ec.Event(text="Something happened", priority=2))

    assert _rule_ids_of_events(event_status) == ["valid"]


@pytest.mark.parametrize(
    "rule_optimizer",
    [
        pytest.param(True, id="switching it off"),
        pytest.param(False, id="switching it on"),
    ],
)
def test_rules_match_while_a_reload_switches_the_rule_optimizer(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: History,
    rule_optimizer: bool,
) -> None:
    reloaded_config = config | {
        "rule_optimizer": rule_optimizer,
        "rule_packs": [_rule_pack("p", _rule("matching"))],
    }
    event_server.reload_configuration(reloaded_config, history)
    # Like during a further reload, the setting changes before the rules compiled for it replace
    # the current ones.
    reloaded_config["rule_optimizer"] = not rule_optimizer

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["matching"]


def test_rule_hits_of_a_changed_rule_start_over_once_the_event_server_uses_it(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("changed"))])
    process_message(event_server, ec.Event(text="Something happened"))
    edited_rule = _rule("changed")
    edited_rule["description"] = "edited"
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", edited_rule)])

    process_message(event_server, ec.Event(text="Something happened"))

    assert list(event_status.get_rule_stats()) == [("changed", 1)]


def test_a_message_counts_no_hit_of_a_rule_a_reload_changed_since_it_matched(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(
        event_server, settings, config, [_rule_pack("pack", _rule("changed"), _rule("unchanged"))]
    )
    # The message ran through these rules ...
    rule_digests = event_status.rule_digests
    edited_rule = _rule("changed")
    edited_rule["description"] = "edited"
    # ... before the reload, but counts its hits after it.
    _reload_configuration(
        event_server, settings, config, [_rule_pack("pack", edited_rule, _rule("unchanged"))]
    )

    event_status.count_rule_match("changed", rule_digests=rule_digests)
    event_status.count_rule_match("unchanged", rule_digests=rule_digests)

    assert list(event_status.get_rule_stats()) == [("unchanged", 1)]
