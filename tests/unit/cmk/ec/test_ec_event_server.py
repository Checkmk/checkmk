#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.utils.hostaddress import HostName

import cmk.ec.export as ec
from cmk.ec.config import Config, MatchGroups
from cmk.ec.main import (
    create_history,
    EventServer,
    EventStatus,
    StatusTableEvents,
    StatusTableHistory,
)

from .helpers import new_event


def _make_rule(state: ec.State) -> ec.Rule:
    return ec.Rule(
        actions=[],
        actions_in_downtime=True,
        autodelete=False,
        cancel_action_phases="always",
        cancel_actions=[],
        comment="",
        description="",
        disabled=False,
        docu_url="",
        id="patterns",
        invert_matching=False,
        sl=ec.ServiceLevel(precedence="message", value=0),
        state=state,
    )


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
    config_rule_packs = config | {"rule_packs": rule_packs}
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

    event_server.process_potential_event(new_event(ec.Event(text="Something happened")))

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

    event_server.process_potential_event(new_event(ec.Event(text="Something happened")))

    assert _rule_ids_of_events(event_status) == ["enabled"]


def test_a_rule_which_skips_its_rule_pack_skips_its_other_rules(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [
        _rule_pack("skipped", _rule("skipping", drop="skip_pack"), _rule("skipped")),
        _rule_pack("next", _rule("next")),
    ]
    _reload_configuration(event_server, settings, config, rule_packs)

    event_server.process_potential_event(new_event(ec.Event(text="Something happened")))

    assert _rule_ids_of_events(event_status) == ["next"]


def test_a_rule_which_drops_the_message_stops_processing_it(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [_rule_pack("pack", _rule("dropping", drop=True), _rule("matching"))]
    _reload_configuration(event_server, settings, config, rule_packs)

    event_server.process_potential_event(new_event(ec.Event(text="Something happened")))

    assert _rule_ids_of_events(event_status) == []


def test_a_cancelling_match_cancels_the_events_of_the_rule(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule = _rule("disk")
    rule["match"] = "disk failed"
    rule["match_ok"] = "disk ok"
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", rule)])
    event_server.process_potential_event(new_event(ec.Event(text="disk failed")))
    assert _rule_ids_of_events(event_status) == ["disk"]

    event_server.process_potential_event(new_event(ec.Event(text="disk ok")))

    assert _rule_ids_of_events(event_status) == []


def test_a_host_name_which_cannot_be_translated_is_empty(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    # Nobody validates settings written by hand.
    config_with_translation = config | {"hostname_translation": {"regex": [("((", "x")]}}
    _reload_configuration(
        event_server, settings, config_with_translation, [_rule_pack("pack", _rule("matching"))]
    )

    event_server.process_potential_event(new_event(ec.Event(text="Something happened")))

    assert [event["host"] for event in event_status.events()] == [""]
