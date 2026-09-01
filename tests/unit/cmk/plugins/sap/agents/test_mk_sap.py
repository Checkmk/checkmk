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


def test_host_prefix_applied_to_sap_and_logwatch(capsys):
    mk_sap.write_piggyback_data(
        host_prefix="S4H_",
        sap_data={"SB1": ["ctx\t0\t  0\tpath\t-\t-\tdetails"]},
        logs={"SB1": {"mylog": ["line1"]}},
    )
    text = capsys.readouterr().out

    # both the sap and the logwatch section land on the same prefixed host
    assert text.count("<<<<S4H_SB1>>>>\n") == 2
    assert "<<<<SB1>>>>\n" not in text
    assert "<<<sap:sep(9)>>>\n" in text
    assert "<<<logwatch>>>\n" in text


def test_no_host_prefix_uses_bare_sid(capsys):
    mk_sap.write_piggyback_data(
        host_prefix="",
        sap_data={"SB1": ["ctx\t0\t  0\tpath\t-\t-\tdetails"]},
        logs={"SB1": {"mylog": ["line1"]}},
    )
    text = capsys.readouterr().out

    assert text.count("<<<<SB1>>>>\n") == 2


def test_host_prefix_and_suffix_wrap_the_sid(capsys):
    mk_sap.write_piggyback_data(
        host_prefix="ECC_",
        host_suffix="_S4H",
        sap_data={"SB1": ["ctx\t0\t  0\tpath\t-\t-\tdetails"]},
        logs={"SB1": {"mylog": ["line1"]}},
    )
    text = capsys.readouterr().out

    assert text.count("<<<<ECC_SB1_S4H>>>>\n") == 2
