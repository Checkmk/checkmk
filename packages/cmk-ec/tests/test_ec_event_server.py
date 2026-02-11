#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config, MatchGroups
from cmk.ec.main import create_history, EventServer, StatusTableEvents, StatusTableHistory

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
    event_server: EventServer,
    settings: ec.Settings,
    config: Config,
    state: ec.State,
    priority: ec.SyslogPriority,
    expected: int,
) -> None:
    rule = _make_rule(state)
    config_rule_packs = config | {"rule_packs": [ec.default_rule_pack([rule])]}
    history = create_history(
        settings,
        config_rule_packs,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )
    event_server.reload_configuration(config_rule_packs, history=history)
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
