#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from tests.testlib import CMKEventConsole

from cmk.utils.hostaddress import HostName

from cmk.ec.config import Config, Rule, ServiceLevel
from cmk.ec.defaults import default_rule_pack
from cmk.ec.event import Event
from cmk.ec.main import (
    create_history,
    EventServer,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.settings import Settings

RULE = Rule(
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
    sl=ServiceLevel(precedence="message", value=0),
    state=("text_pattern", {"1": "supercrit", "2": "superwarn"}),
)


def test_event_rewrite(
    event_server: EventServer,
    settings: Settings,
    config: Config,
) -> None:
    """
    Event server rewrite_event() method should change event state
    even if incomplete StatePatterns are given in rule["State"].
    """
    config_rule_packs: Config = {**config, "rule_packs": [default_rule_pack([RULE])]}
    history = create_history(
        settings,
        config_rule_packs,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )
    event_server.reload_configuration(config_rule_packs, history=history)
    event = CMKEventConsole.new_event(
        Event(
            host=HostName("heute"),
            text="SUPERWARN",
            core_host=HostName("heute"),
        )
    )
    assert "state" not in event

    event_server.rewrite_event(rule=RULE, event=event, match_groups={})

    assert event["text"] == "SUPERWARN"
    assert event["state"] == 2
