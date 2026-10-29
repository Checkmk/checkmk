#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import datetime
from collections import namedtuple
from unittest.mock import ANY

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

    def discover(self, what):  # noqa: ARG002
        return self

    def call(self, func_name, **kwargs):  # noqa: ARG002
        return self

    def create_function_call(self):
        return self

    def __getitem__(self, x):
        return getattr(self, x)


@pytest.mark.usefixtures("monkeypatch")
def test_empty_tree() -> None:
    fake_connection_tree = FakeConnectionTree({})
    result = mk_sap.mon_tree(
        fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name"
    )
    assert result == {}


@pytest.mark.usefixtures("monkeypatch")
def test_simple_tree() -> None:
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


@pytest.mark.usefixtures("monkeypatch")
def test_recursion_simple() -> None:
    fake_connection_tree = FakeConnectionTree(
        [
            # this element says it is it's own parent.
            # this happened for three different customer: SUP-6945 SUP-9293 SUP-9015
            {"MTNAMESHRT": "root", "ALPARINTRE": 1},
        ]
    )
    with pytest.raises(mk_sap.SapError):
        mk_sap.mon_tree(fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name")


@pytest.mark.usefixtures("monkeypatch")
def test_recursion() -> None:
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


_CRITICAL_NUMBER_RANGES = (
    "SAP CCMS Technical Expert Monitors/All Monitoring Contexts/Critical Number Ranges"
)
_ALL_CLIENTS = _CRITICAL_NUMBER_RANGES + "/Critical Number Ranges All Clients"
_EXCLUDE_CLIENT_000 = _ALL_CLIENTS + "/Client 000 Alert Messages for Number Ran*"


@pytest.mark.parametrize(
    "monitor, exclude, path, toplevel_match, expected",
    [
        pytest.param(
            ["SAP CCMS Monitor Templates/Dialog Overview/*"],
            [],
            "SAP CCMS Monitor Templates/Other/Foo",
            False,
            False,
            id="nothing matches",
        ),
        pytest.param(
            [_CRITICAL_NUMBER_RANGES + "/*"],
            [_EXCLUDE_CLIENT_000],
            _ALL_CLIENTS + "/Client 000 Alert Messages for Number Ran",
            False,
            False,
            id="exclude wins over a matching monitor rule (last segment truncated to 40 chars)",
        ),
        pytest.param(
            [_CRITICAL_NUMBER_RANGES + "/*"],
            [_EXCLUDE_CLIENT_000],
            _ALL_CLIENTS + "/Client 100 Alert Messages for Number Ran",
            False,
            True,
            id="a sibling not matching the exclude rule stays monitored",
        ),
        pytest.param(
            [_CRITICAL_NUMBER_RANGES + "/*"],
            [_EXCLUDE_CLIENT_000],
            "SAP CCMS Technical Expert Monitors/All Monitoring Contexts",
            True,
            True,
            id="subtree exclude is not shortened, so toplevel matching keeps the monitor",
        ),
        pytest.param(
            ["*"],
            ["SAP CCMS Monitor Templates/Dialog Overview*"],
            "SAP CCMS Monitor Templates/Dialog Overview",
            True,
            False,
            id="exclude matching the toplevel path skips the whole monitor",
        ),
    ],
)
def test_to_be_monitored(monkeypatch, monitor, exclude, path, toplevel_match, expected):  # type: ignore[misc]
    monkeypatch.setattr(mk_sap, "monitor_paths", monitor)
    monkeypatch.setattr(mk_sap, "exclude_paths", exclude)
    assert mk_sap.to_be_monitored(path, toplevel_match) is expected


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


def test_sent_alerts_survive_a_state_file_round_trip(monkeypatch, tmp_path):
    states = {("PRD", "logfile"): {"20261007100000-0123456789abcdef": (1000, "W ÄLERT")}}
    state_file = tmp_path / "sap.state"
    state_file.write_text(mk_sap.serialize_states(states), encoding="utf-8")
    monkeypatch.setattr(mk_sap, "STATE_FILE", str(state_file))
    assert mk_sap.load_state_file() == states


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
        # values must be datetimes or dicts of (time first sent, line or None),
        # anything else would break alert processing later on
        "{('PRD', 'logfile'): 5}",
        "{('PRD', 'logfile'): (2026, 6, 10, 9, 30, 0), ('PRD', 'other'): 'bogus'}",
        "{('PRD', 'logfile'): {'20261007100000-0123456789abcdef': 5}}",
        "{('PRD', 'logfile'): {'20261007100000-0123456789abcdef': ('1000', 'W ALERT')}}",
        "{('PRD', 'logfile'): {'20261007100000-0123456789abcdef': (1000, 5)}}",
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


_NODE = {
    "MTSYSID": "PRD",
    "MTMCNAME": "sapprd01_PRD_00",
    "PATH": "SAP CCMS Monitor Templates/Dialog Overview/Syslog",
}

_LOGFILE = "sapprd01_PRD_00/SAP CCMS Monitor Templates/Dialog Overview/Syslog"


class _FakeConnection:
    def call(self, _function_name, **parameters):
        return {"VALUE": {"VALUE": 2}, "XMI_EXT_MSG": {"MSG": parameters["AID"]["ALUNIQNUM"]}}


def _alert(alert_time, message):
    return {
        "ALSYSID": "PRD",
        "MSEGNAME": "SAPCCMSR",
        "ALUNIQNUM": message,
        "ALINDEX": "1",
        "ALERTDATE": "20261007",
        "ALERTTIME": alert_time,
    }


def _process_alerts(connection, cfg_entry, alerts, now):
    return mk_sap.process_alerts(connection, cfg_entry, {}, "", "", _NODE, alerts, now)


def _logwatch_lines(connection, alerts, now, cfg_entry=None):
    # every call is a new agent run, which starts without processed logfiles
    mk_sap.logfiles.clear()
    logs = _process_alerts(connection, cfg_entry or {"user": "cmkmon"}, alerts, now)
    return logs["PRD"][_LOGFILE]


@pytest.fixture(name="plugin_states")
def fixture_plugin_states(monkeypatch):
    monkeypatch.setattr(mk_sap, "states", {})
    monkeypatch.setattr(mk_sap, "logfiles", [])
    monkeypatch.setattr(mk_sap, "state_file_changed", False)
    return mk_sap.states


@pytest.mark.usefixtures("plugin_states")
def test_alert_is_sent_again_until_the_retention_period_has_passed() -> None:
    alerts = [_alert("100000", "ALERT-A")]
    _logwatch_lines(_FakeConnection(), alerts, now=1000)

    lines = _logwatch_lines(None, alerts, now=1000 + mk_sap.retention_period)

    assert lines == ["BATCH: 20261007100000-290addf3eba47f75", "W 2026-10-07 10:00:00 ALERT-A"]


@pytest.mark.usefixtures("plugin_states")
def test_alert_is_not_sent_after_the_retention_period() -> None:
    alerts = [_alert("100000", "ALERT-A")]
    _logwatch_lines(_FakeConnection(), alerts, now=1000)

    lines = _logwatch_lines(None, alerts, now=1000 + mk_sap.retention_period + 1)

    assert lines == []


@pytest.mark.parametrize(
    "alert_time, expected_line",
    [
        pytest.param("100000", "W 2026-10-07 10:00:00 ALERT-B", id="same second"),
        pytest.param("095900", "W 2026-10-07 09:59:00 ALERT-B", id="older"),
    ],
)
@pytest.mark.usefixtures("plugin_states")
def test_new_alert_is_sent_in_a_new_batch_whatever_its_time(alert_time, expected_line):  # type: ignore[misc]
    sent_alert = _alert("100000", "ALERT-A")
    first_lines = _logwatch_lines(_FakeConnection(), [sent_alert], now=1000)

    lines = _logwatch_lines(
        _FakeConnection(), [sent_alert, _alert(alert_time, "ALERT-B")], now=1060
    )

    assert lines == first_lines + [ANY, expected_line]
    assert lines[2] != first_lines[0]


@pytest.mark.parametrize(
    "cfg_entry",
    [
        pytest.param({"user": "cmkmon"}, id="sid as host name"),
        pytest.param({"user": "cmkmon", "host_prefix": "X_"}, id="prefixed host name"),
    ],
)
def test_alerts_reported_by_older_versions_are_not_sent_again(plugin_states, cfg_entry):  # type: ignore[misc]
    plugin_states[("PRD", _LOGFILE)] = datetime.datetime(2026, 10, 7, 10, 0, 0)
    alerts = [_alert("100000", "ALERT-OLD"), _alert("100100", "ALERT-NEW")]

    lines = _logwatch_lines(_FakeConnection(), alerts, now=1000, cfg_entry=cfg_entry)

    assert lines == [ANY, "W 2026-10-07 10:01:00 ALERT-NEW"]


@pytest.mark.usefixtures("plugin_states")
def test_alerts_sent_by_an_earlier_cfg_entry_of_the_run_are_not_sent_again() -> None:
    same_system = {"user": "cmkmon", "host_prefix": "X_"}
    alerts = [_alert("100000", "ALERT-A")]
    _logwatch_lines(_FakeConnection(), alerts, now=1000, cfg_entry=same_system)

    logs = _process_alerts(_FakeConnection(), same_system, alerts, now=1000)

    assert logs == {}


@pytest.mark.parametrize("option", ["host_prefix", "host_suffix"])
@pytest.mark.usefixtures("plugin_states")
def test_systems_with_the_same_sid_are_sent_their_own_alerts(option):  # type: ignore[misc]
    _logwatch_lines(
        _FakeConnection(), [_alert("100000", "ALERT-A")], 1000, {"user": "cmkmon", option: "A"}
    )

    logs = _process_alerts(
        _FakeConnection(), {"user": "cmkmon", option: "B"}, [_alert("100000", "ALERT-B")], 1000
    )

    assert logs["PRD"][_LOGFILE] == [ANY, "W 2026-10-07 10:00:00 ALERT-B"]


@pytest.mark.parametrize("option", ["host_prefix", "host_suffix"])
@pytest.mark.usefixtures("plugin_states")
def test_systems_with_the_same_sid_keep_separate_states(option):  # type: ignore[misc]
    first_system = {"user": "cmkmon", option: "A"}
    alerts = [_alert("100000", "ALERT-A")]
    _logwatch_lines(_FakeConnection(), alerts, now=1000, cfg_entry=first_system)
    _process_alerts(
        _FakeConnection(), {"user": "cmkmon", option: "B"}, [_alert("100000", "ALERT-B")], 1000
    )

    # None as connection fails if the alert details are fetched again
    lines = _logwatch_lines(None, alerts, now=1060, cfg_entry=first_system)

    assert lines == [ANY, "W 2026-10-07 10:00:00 ALERT-A"]
