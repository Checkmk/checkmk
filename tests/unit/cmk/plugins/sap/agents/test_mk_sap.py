#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import datetime
from collections import namedtuple

import pytest

from cmk.plugins.sap.agents import mk_sap

Value = namedtuple("Value", ["value"])


class FakeConnectionTree:
    def __init__(self, tree_data):
        self.tree_data = tree_data

    def EXTERNAL_USER_NAME(self, value):
        pass

    def MONITOR_NAME(self, value):
        pass

    @property
    def TREE_NODES(self):
        return self.tree_data

    @property
    def RETURN(self):
        return {"TYPE": "NOT_E"}

    def invoke(self):
        pass

    def discover(self, what):
        return self

    def call(self, func_name, **kwargs):
        return self

    def create_function_call(self):
        return self

    def __getitem__(self, x):
        return getattr(self, x)


def test_empty_tree(monkeypatch):
    fake_connection_tree = FakeConnectionTree({})
    result = mk_sap.mon_tree(
        fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name"
    )
    assert result == {}


def test_simple_tree(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            {"MTNAMESHRT": "root", "ALPARINTRE": 0},
            {"MTNAMESHRT": "02", "ALPARINTRE": 3},
            {"MTNAMESHRT": "01", "ALPARINTRE": 1},
        ]
    )
    result = mk_sap.mon_tree(
        fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name"
    )

    assert result == [
        {"ALPARINTRE": 0, "MTNAMESHRT": "root", "PATH": "apu_ms_name/root"},
        {"ALPARINTRE": 3, "MTNAMESHRT": "02", "PATH": "apu_ms_name/root/01/02"},
        {"ALPARINTRE": 1, "MTNAMESHRT": "01", "PATH": "apu_ms_name/root/01"},
    ]


def test_recursion_simple(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            # this element says it is it's own parent.
            # this happened for three different customer: SUP-6945 SUP-9293 SUP-9015
            {"MTNAMESHRT": "root", "ALPARINTRE": 1},
        ]
    )
    with pytest.raises(mk_sap.SapError):
        mk_sap.mon_tree(fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name")


def test_recursion(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            # here the recursion is build over multiple elements:
            # 01 parent: 03, 03 parent 02, 02 parent 01
            {"MTNAMESHRT": "01", "ALPARINTRE": 3},
            {"MTNAMESHRT": "02", "ALPARINTRE": 1},
            {"MTNAMESHRT": "03", "ALPARINTRE": 2},
        ]
    )
    with pytest.raises(mk_sap.SapError) as exception:
        mk_sap.mon_tree(fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name")
        assert "01" in str(exception.value)


STATES = {
    ("PRD", "Other/SAP CCMS Monitor Templates/Dialog Overview/Syslog"): datetime.datetime(
        2026, 6, 10, 9, 30, 0
    )
}


@pytest.mark.parametrize(
    "monitor, exclude, path, toplevel_match, expected",
    [
        # default behaviour without exclude_paths stays untouched
        (["SAP CCMS Monitor Templates/Dialog Overview/*"], [], "SAP CCMS Monitor Templates/Dialog Overview/ResponseTime", False, True),
        (["SAP CCMS Monitor Templates/Dialog Overview/*"], [], "SAP CCMS Monitor Templates/Other Monitor/Foo", False, False),
        # toplevel matching shortens monitor rules to the first two segments
        (["SAP CCMS Monitor Templates/Dialog Overview/ResponseTime"], [], "SAP CCMS Monitor Templates/Dialog Overview", True, True),
        # a matching exclude rule wins over a matching monitor rule.
        # Note the truncated last path segment: segments come from the
        # 40 character SAP field MTNAMESHRT, patterns must match the
        # truncated name (pattern anchored to the subtree as recommended
        # in sap.cfg)
        (
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/*"],
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/Critical Number Ranges All Clients/Client 000 Alert Messages for Number Ran*"],
            "SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/Critical Number Ranges All Clients/Client 000 Alert Messages for Number Ran",
            False,
            False,
        ),
        # sibling nodes not matching the exclude rule are still monitored
        (
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/*"],
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/Critical Number Ranges All Clients/Client 000 Alert Messages for Number Ran*"],
            "SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/Critical Number Ranges All Clients/Client 100 Alert Messages for Number Ran",
            False,
            True,
        ),
        # an exclude rule targeting a subtree node must not skip the whole
        # monitor during toplevel matching (exclude rules are not shortened)
        (
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/*"],
            ["SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges/Critical Number Ranges All Clients/Client 000 Alert Messages for Number Ran*"],
            "SAP CCMS Technical Expert Monitors/All Monitoring Contexts",
            True,
            True,
        ),
        # an exclude rule matching the toplevel path skips the whole monitor
        (
            ["*"],
            ["SAP CCMS Monitor Templates/Dialog Overview*"],
            "SAP CCMS Monitor Templates/Dialog Overview",
            True,
            False,
        ),
    ],
)
def test_to_be_monitored(monkeypatch, monitor, exclude, path, toplevel_match, expected):
    monkeypatch.setattr(mk_sap, "monitor_paths", monitor)
    monkeypatch.setattr(mk_sap, "exclude_paths", exclude)
    assert mk_sap.to_be_monitored(path, toplevel_match) is expected


def test_state_file_round_trip(monkeypatch, tmp_path):
    state_file = tmp_path / "sap.state"
    state_file.write_text(mk_sap.serialize_states(STATES))
    monkeypatch.setattr(mk_sap, "STATE_FILE", str(state_file))
    assert mk_sap.load_state_file() == STATES


def test_state_file_legacy_datetime_format(monkeypatch, tmp_path):
    state_file = tmp_path / "sap.state"
    state_file.write_text(repr(STATES))
    monkeypatch.setattr(mk_sap, "STATE_FILE", str(state_file))
    assert mk_sap.load_state_file() == STATES


def test_state_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(mk_sap, "STATE_FILE", str(tmp_path / "sap.state"))
    assert mk_sap.load_state_file() == {}


@pytest.mark.parametrize(
    "content",
    [
        "foo(",
        "__import__('os').system('true')",
        "{('PRD', 'logfile'): open('/etc/passwd')}",
        "",
        # tz-aware datetimes cannot be written by the plugin; keyword
        # arguments are rejected instead of silently dropping the tzinfo
        "{('PRD', 'logfile'): datetime.datetime(2026, 6, 10, 9, 30, tzinfo=datetime.timezone.utc)}",
        # values must be datetimes, anything else would break alert
        # processing later on
        "{('PRD', 'logfile'): 5}",
        "{('PRD', 'logfile'): (2026, 6, 10, 9, 30, 0), ('PRD', 'other'): 'bogus'}",
    ],
)
def test_state_file_corrupt(monkeypatch, tmp_path, content):  # type: ignore[misc]
    state_file = tmp_path / "sap.state"
    state_file.write_text(content)
    monkeypatch.setattr(mk_sap, "STATE_FILE", str(state_file))
    assert mk_sap.load_state_file() == {}
