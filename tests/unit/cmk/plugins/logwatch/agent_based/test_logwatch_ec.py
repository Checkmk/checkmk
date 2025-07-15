#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest

from tests.unit.cmk.base.emptyconfig import EMPTYCONFIG

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths

from cmk.base import config

import cmk.ec.export as ec

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.logwatch.agent_based import commons as logwatch_
from cmk.plugins.logwatch.agent_based import logwatch_ec
from cmk.plugins.logwatch.agent_based.logwatch_section import parse_logwatch

_STRING_TABLE_NO_MESSAGES = [
    ["[[[log1]]]"],
    ["[[[log2]]]"],
    ["[[[log3:missing]]]"],
    ["[[[log4:cannotopen]]]"],
    ["[[[log5]]]"],
    ["[[[log1:missing]]]"],
]

_STRING_TABLE_MESSAGES_LOG1 = [
    ["[[[log1]]]"],
    ["BATCH: 1680617834-122172169179246007103019047128114004006211120121"],
    ["C ERROR: issue 1"],
    ["C ERROR: issue 2"],
    ["[[[log2]]]"],
    ["[[[log3:missing]]]"],
    ["[[[log4:cannotopen]]]"],
    ["[[[log5]]]"],
    ["[[[log1:missing]]]"],
]

_STRING_TABLE_MESSAGES_LOG1_2 = [
    ["[[[log1]]]"],
    ["BATCH: 1680617840-135239174175144102013221144181058125008119107236"],
    ["C ERROR: issue 1"],
    ["C ERROR: issue 2"],
    ["C ERROR: issue 3"],
]

_STRING_TABLE_MESSAGES_LOG5 = [
    ["[[[log2]]]"],
    ["[[[log3:missing]]]"],
    ["[[[log4:cannotopen]]]"],
    ["[[[log5]]]"],
    ["BATCH: 1680617711-122172169179246007103019047128114004006211120555"],
    ["C ERROR: issue 1"],
    ["C ERROR: issue 2"],
]


SECTION1 = logwatch_.Section(
    errors=[],
    logfiles={
        "log1": {
            "attr": "ok",
            "lines": {
                "test": [
                    "W This long message should be written to one spool file",
                    "C And this long message should be written to another spool file",
                    "W This last long message should be written to a third spool file",
                ]
            },
        },
    },
)

DEFAULT_TEST_PARAMETERS = logwatch_.ParameterLogwatchEc(
    {
        **logwatch_ec.CHECK_DEFAULT_PARAMETERS,
        "service_level": 10,
        "host_name": "test-host",
    }
)


def _patch_config_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        config.access_globally_cached_config_cache.__name__,
        lambda: config.ConfigCache(EMPTYCONFIG),
    )


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (_STRING_TABLE_NO_MESSAGES, [], []),
        (
            _STRING_TABLE_NO_MESSAGES,
            [{"separate_checks": True}],
            [
                Service(item="log1", parameters={"expected_logfiles": ["log1"]}),
                Service(item="log2", parameters={"expected_logfiles": ["log2"]}),
                Service(item="log4", parameters={"expected_logfiles": ["log4"]}),
                Service(item="log5", parameters={"expected_logfiles": ["log5"]}),
            ],
        ),
        (_STRING_TABLE_NO_MESSAGES, [{"restrict_logfiles": [".*"]}], []),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                {
                    "restrict_logfiles": [".*"],
                    "separate_checks": True,
                }
            ],
            [
                Service(item="log1", parameters={"expected_logfiles": ["log1"]}),
                Service(item="log2", parameters={"expected_logfiles": ["log2"]}),
                Service(item="log4", parameters={"expected_logfiles": ["log4"]}),
                Service(item="log5", parameters={"expected_logfiles": ["log5"]}),
            ],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                {
                    "restrict_logfiles": [".*"],
                    "separate_checks": False,
                }
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                {
                    "restrict_logfiles": [".*"],
                }
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                {
                    "restrict_logfiles": ["log1"],
                    "separate_checks": True,
                    "method": "pass me on!",
                    "facility": "pass me on!",
                    "monitor_logfilelist": "pass me on!",
                    "monitor_logfile_access_state": "pass me on!",
                    "logwatch_reclassify": "pass me on!",
                    "some_other_key": "I should be discarded!",
                }
            ],
            [
                Service(
                    item="log1",
                    parameters={
                        "expected_logfiles": ["log1"],
                        "method": "pass me on!",
                        "facility": "pass me on!",
                        "monitor_logfilelist": "pass me on!",
                        "monitor_logfile_access_state": "pass me on!",
                        "logwatch_reclassify": "pass me on!",
                    },
                ),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_single(
    monkeypatch: pytest.MonkeyPatch,
    info: StringTable,
    fwd_rule: Mapping[str, object],
    expected_result: DiscoveryResult,
) -> None:
    parsed = parse_logwatch(info)

    monkeypatch.setattr(
        logwatch_.RulesetAccess,
        logwatch_.RulesetAccess.logwatch_ec_all.__name__,
        lambda _host: fwd_rule,
    )
    actual_result = sorted(
        logwatch_ec.discover_single(parsed, {"host_name": "test-host"}), key=lambda s: s.item or ""
    )
    assert actual_result == expected_result


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (_STRING_TABLE_NO_MESSAGES, [], []),
        (_STRING_TABLE_NO_MESSAGES, [{"separate_checks": True}], []),
        (
            _STRING_TABLE_NO_MESSAGES,
            [{"separate_checks": False}],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2", "log4", "log5"]}),
            ],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [{"restrict_logfiles": [".*[12]"], "separate_checks": False}],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2"]}),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_groups(
    monkeypatch: pytest.MonkeyPatch,
    info: StringTable,
    fwd_rule: Mapping[str, object],
    expected_result: DiscoveryResult,
) -> None:
    parsed = parse_logwatch(info)

    monkeypatch.setattr(
        logwatch_.RulesetAccess,
        logwatch_.RulesetAccess.logwatch_ec_all.__name__,
        lambda _host: fwd_rule,
    )
    actual_result = list(logwatch_ec.discover_group(parsed, {"host_name": "test-host"}))
    assert actual_result == expected_result


class _FakeForwarder:
    def __call__(
        self,
        method: str | tuple,
        messages: Sequence[ec.SyslogMessage],
        timestamp: float,
    ) -> logwatch_ec.LogwatchForwardedResult:
        return logwatch_ec.LogwatchForwardedResult(num_forwarded=len(messages))


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "log1",
            DEFAULT_TEST_PARAMETERS,
            {"node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES)},
            [
                Result(state=State.OK, summary="Forwarded 0 messages"),
                Metric("messages", 0.0),
            ],
        ),
        (
            "log4",
            {
                "facility": 17,  # default to "local1"
                "method": "",  # local site
                "monitor_logfilelist": False,
                "monitor_logfile_access_state": 2,
                "expected_logfiles": ["log4"],
                "host_name": "test-host",
                "service_level": 10,
            },
            {"node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES)},
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 0 messages"),
                Metric("messages", 0.0),
            ],
        ),
    ],
)
def test_check_logwatch_ec_common_single_node(
    item: str | None,
    params: logwatch_.ParameterLogwatchEc,
    parsed: logwatch_.ClusterSection,
    expected_result: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config_cache(monkeypatch)
    assert (
        list(
            logwatch_ec.check_logwatch_ec_common(
                item,
                params,
                parsed,
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store={},
                message_forwarder=_FakeForwarder(),
            )
        )
        == expected_result
    )


def test_check_logwatch_ec_common_single_node_item_missing() -> None:
    assert not list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=_FakeForwarder(),
        )
    )


def test_check_logwatch_ec_common_single_node_log_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_config_cache(monkeypatch)
    actual_result = list(
        logwatch_ec.check_logwatch_ec_common(
            "log3",
            {
                "facility": 17,  # default to "local1"
                "method": "",  # local site
                "monitor_logfilelist": True,
                "monitor_logfile_access_state": 2,
                "expected_logfiles": ["log3"],
                "service_level": 10,
                "host_name": "test-host",
            },
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=_FakeForwarder(),
        )
    )

    assert actual_result == [
        Result(state=State.WARN, summary="Missing logfiles: log3 (on node1)"),
        Result(state=State.OK, summary="Forwarded 0 messages"),
        Metric("messages", 0.0),
    ]


@pytest.mark.parametrize(
    ["cluster_section", "expected_result"],
    [
        pytest.param(
            {
                "node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
                "node2": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
            },
            [
                Result(state=State.OK, summary="Forwarded 0 messages"),
                Metric("messages", 0.0),
            ],
            id="no messages",
        ),
        pytest.param(
            {
                "node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
            },
            [
                Result(state=State.OK, summary="Forwarded 2 messages from log1"),
                Metric("messages", 2.0),
            ],
            id="messages on one node",
        ),
        pytest.param(
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1_2),
            },
            [
                Result(state=State.OK, summary="Forwarded 5 messages from log1"),
                Metric("messages", 5.0),
            ],
            id="messages on both nodes",
        ),
    ],
)
def test_check_logwatch_ec_common_multiple_nodes_grouped(
    cluster_section: logwatch_.ClusterSection,
    expected_result: CheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config_cache(monkeypatch)
    assert (
        list(
            logwatch_ec.check_logwatch_ec_common(
                "log1",
                DEFAULT_TEST_PARAMETERS,
                cluster_section,
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store={},
                message_forwarder=_FakeForwarder(),
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["params", "cluster_section", "expected_result"],
    [
        pytest.param(
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
                "node2": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
            },
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.CRIT, summary="[node2] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 0 messages"),
                Metric("messages", 0.0),
            ],
            id="no messages",
        ),
        pytest.param(
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
            },
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.CRIT, summary="[node2] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 2 messages from log1"),
                Metric("messages", 2.0),
            ],
            id="messages on one node",
        ),
        pytest.param(
            {
                "facility": 17,  # default to "local1"
                "method": "",  # local site
                "monitor_logfilelist": False,
                "monitor_logfile_access_state": 2,
                "expected_logfiles": ["log4"],
                "service_level": 10,
            },
            {
                "node1": parse_logwatch(_STRING_TABLE_NO_MESSAGES),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
            },
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.CRIT, summary="[node2] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 2 messages from log1"),
                Metric("messages", 2.0),
            ],
            id="no access to logfile on both nodes",
        ),
        pytest.param(
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1_2),
            },
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 5 messages from log1"),
                Metric("messages", 5.0),
            ],
            id="messages on both nodes, same logfile",
        ),
        pytest.param(
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
            },
            [
                Result(state=State.CRIT, summary="[node1] Could not read log file 'log4'"),
                Result(state=State.CRIT, summary="[node2] Could not read log file 'log4'"),
                Result(state=State.OK, summary="Forwarded 4 messages from log1, log5"),
                Metric("messages", 4.0),
            ],
            id="messages on both nodes, different logfiles",
        ),
    ],
)
@pytest.mark.skip("Flaky test - will be re-enabled with CMK-17338")
def test_check_logwatch_ec_common_multiple_nodes_ungrouped(
    params: logwatch_.ParameterLogwatchEc,
    cluster_section: logwatch_.ClusterSection,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            logwatch_ec.check_logwatch_ec_common(
                None,
                params,
                cluster_section,
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store={},
                message_forwarder=_FakeForwarder(),
            )
        )
        == expected_result
    )


def test_check_logwatch_ec_common_multiple_nodes_item_completely_missing() -> None:
    assert not list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=_FakeForwarder(),
        )
    )


def test_check_logwatch_ec_common_multiple_nodes_item_partially_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config_cache(monkeypatch)
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            DEFAULT_TEST_PARAMETERS,
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG5),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=_FakeForwarder(),
        )
    ) == [
        Result(state=State.OK, summary="Forwarded 2 messages from log1"),
        Metric("messages", 2.0),
    ]


def test_check_logwatch_ec_common_multiple_nodes_logfile_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config_cache(monkeypatch)
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log3",
            {
                "facility": 17,  # default to "local1"
                "method": "",  # local site
                "monitor_logfilelist": True,
                "monitor_logfile_access_state": 2,
                "expected_logfiles": ["log3"],
                "service_level": 10,
                "host_name": "test-host",
            },
            {
                "node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
                "node2": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=_FakeForwarder(),
        )
    ) == [
        Result(state=State.WARN, summary="Missing logfiles: log3 (on node1, node2)"),
        Result(state=State.OK, summary="Forwarded 0 messages"),
        Metric("messages", 0.0),
    ]


def test_check_logwatch_ec_common_spool(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_config_cache(monkeypatch)
    monkeypatch.setattr(logwatch_ec, "_MAX_SPOOL_SIZE", 32)
    assert list(
        logwatch_ec.check_logwatch_ec_common(
            "log1",
            {
                **DEFAULT_TEST_PARAMETERS,
                "method": "spool:",
            },
            {
                "node1": SECTION1,
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store={},
            message_forwarder=logwatch_ec.MessageForwarder("log1", HostName("test-host")),
        )
    ) == [
        Result(state=State.OK, summary="Forwarded 3 messages from log1"),
        Metric("messages", 3.0),
    ]
    assert len(list(Path(cmk.utils.paths.omd_root, "var/mkeventd/spool").iterdir())) == 3


class FakeTcpError(Exception):
    pass


class FakeTcpErrorRaised(Exception):
    pass


def _forward_message(
    tcp_result: Literal["ok", "raise exception", "set exception"],
    method: tuple[str, dict[str, object]] = ("tcp", {"address": "127.0.0.1", "port": 127001}),
    text: str = "some_text",
    item: str | None = None,
    application: str = "-",
    timestamp: str = "2023-11-11 11:11:00Z",
) -> tuple[logwatch_ec.LogwatchForwardedResult, list[tuple[float, int, list[str]]]]:
    messages_forwarded: list[tuple[float, int, list[str]]] = []

    class TestForwardTcpMessageForwarder(logwatch_ec.MessageForwarder):
        @staticmethod
        def _forward_send_tcp(method, message_chunks, result):
            nonlocal messages_forwarded
            if tcp_result == "ok":
                for message in message_chunks:
                    messages_forwarded.append(message)
                    result.num_forwarded += 1
            elif tcp_result == "set exception":
                result.exception = FakeTcpError("could not send messages")
            elif tcp_result == "raise exception":
                raise FakeTcpErrorRaised("rise and shine")
            else:
                raise NotImplementedError()

    result = TestForwardTcpMessageForwarder(item=item, hostname=HostName("some_host_name"))(
        method=method,
        messages=[
            ec.SyslogMessage(
                facility=1, severity=1, timestamp=0.0, text=text, application=application
            )
        ],
        timestamp=datetime.datetime.fromisoformat(timestamp).timestamp(),
    )

    return result, messages_forwarded


def test_forward_tcp_message_forwarded_ok() -> None:
    result, messages_forwarded = _forward_message(tcp_result="ok")
    assert result == logwatch_ec.LogwatchForwardedResult(
        num_forwarded=1,
        num_spooled=0,
        num_dropped=0,
        exception=None,
    )

    assert len(messages_forwarded) == 1
    # first element of message is a timestamp!
    assert messages_forwarded[0][1:] == (
        0,
        ["<9>1 1970-01-01T00:00:00+00:00 - - - - [Checkmk@18662] some_text"],
    )


def test_forward_tcp_message_forwarded_nok_1() -> None:
    result, messages_forwarded = _forward_message(tcp_result="set exception")

    assert result.num_forwarded == 0
    assert result.num_spooled == 0
    assert result.num_dropped == 1
    assert isinstance(result.exception, FakeTcpError)

    assert len(messages_forwarded) == 0


def test_forward_tcp_message_forwarded_nok_2() -> None:
    result, messages_forwarded = _forward_message(tcp_result="raise exception")

    assert result.num_forwarded == 0
    assert result.num_spooled == 0
    assert result.num_dropped == 1
    assert isinstance(result.exception, FakeTcpErrorRaised)

    assert len(messages_forwarded) == 0


SPOOL_METHOD = (
    "tcp",
    {
        "address": "127.0.0.1",
        "port": 127001,
        "spool": {"max_age": 60 * 60, "max_size": 1024 * 1024},
    },
)


def test_forward_tcp_message_forwarded_spool() -> None:
    # could not send message, so spool it
    result, messages_forwarded = _forward_message(
        tcp_result="set exception", method=SPOOL_METHOD, text="spooled"
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 1
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # sending works again, so send both of them
    result, messages_forwarded = _forward_message(
        tcp_result="ok", method=SPOOL_METHOD, text="directly_sent_1"
    )
    assert result.num_forwarded == 2
    assert result.num_spooled == 0
    assert result.num_dropped == 0
    assert len(messages_forwarded) == 2

    assert messages_forwarded[0][2][0].rsplit(" ", 1)[-1] == "spooled"
    assert messages_forwarded[1][2][0].rsplit(" ", 1)[-1] == "directly_sent_1"

    # sending is still working, so send only one
    result, messages_forwarded = _forward_message(
        tcp_result="ok", method=SPOOL_METHOD, text="directly_sent_2"
    )
    assert result.num_forwarded == 1
    assert result.num_spooled == 0
    assert result.num_dropped == 0
    assert len(messages_forwarded) == 1

    assert messages_forwarded[0][2][0].rsplit(" ", 1)[-1] == "directly_sent_2"


def test_forward_tcp_message_forwarded_spool_twice() -> None:
    # we delete the original spool file after reading it.
    # here we want to make sure, that the spool file is recreated. otherwise messages from different
    # time would land into the same spool file and may not be correctly cleaned up.
    spool_dir = cmk.utils.paths.var_dir / "logwatch_spool/some_host_name"

    # create a spooled message:
    result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        method=SPOOL_METHOD,
        timestamp="2023-10-31 16:02:00Z",
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 1
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # we expect one spool file to be created:
    assert list(f.name for f in spool_dir.iterdir()) == ["spool.1698768120.00"]

    # create another spooled message:
    result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        method=SPOOL_METHOD,
        timestamp="2023-10-31 16:03:00Z",
    )
    assert result.num_forwarded == 0
    assert result.num_spooled == 2
    assert result.num_dropped == 0
    assert isinstance(result.exception, FakeTcpError)
    assert len(messages_forwarded) == 0

    # now let's see if we have two spool files
    assert {f.name for f in spool_dir.iterdir()} == {
        "spool.1698768120.00",
        "spool.1698768180.00",
    }


def test_forward_tcp_message_update_old_spoolfiles() -> None:
    # can be removed with checkmk 2.4.0
    spool_dir = cmk.utils.paths.var_dir / "logwatch_spool/some_host_name"
    # logwatch_ec with separate_checks = True creates one service per syslog application, but they
    # shared one folder for their spool files. this led to problems when writing spool-files
    # (overwriting each other) and reading spool-files (all items read all spool-files).
    # with werk 15307 it was introduced that each service get its own subfolder for spool-files.
    # here we want to check the update process: spool-files from the host-folder should be
    # read and moved to the correct subfolder.

    # first we create a spooled message for a logwatch_ec service with "separate_checks" = False
    # this is the same as the old behaviour, before werk 15397 with "separate_checks" = True
    _result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        method=SPOOL_METHOD,
        application="item_name_1",
        timestamp="2023-10-31 16:02:00Z",
    )
    # we expect one spool file to be created:
    assert list(f.name for f in spool_dir.iterdir()) == ["spool.1698768120.00"]

    # now we do the same, but for a different item:
    _result, messages_forwarded = _forward_message(
        tcp_result="set exception",
        method=SPOOL_METHOD,
        application="another_item",
        timestamp="2023-10-31 16:03:00Z",
    )
    # we expect two spool files in the host folder:
    assert {f.name for f in spool_dir.iterdir()} == {
        "spool.1698768120.00",
        "spool.1698768180.00",
    }

    # this was the old behaviour. now we image the customer installed the new version of checkmk.
    # their logwatch_ec services had separate_checks = True from the beginning.

    _result, messages_forwarded = _forward_message(
        tcp_result="ok",
        method=SPOOL_METHOD,
        item="item_name_1",
        application="item_name_1",
        timestamp="2023-10-31 16:04:00Z",
    )

    # we now expect, that the item_name_1 message was found (although in the old directory) and the
    # new message was also sent:
    assert len(messages_forwarded) == 2

    # and we also expect, the spool-file of another_item to be left alone:
    assert list(f.name for f in spool_dir.iterdir() if f.is_file()) == [
        "spool.1698768180.00",
    ]
    # and a folder which held the spooled message for a short time
    assert list(f.name for f in spool_dir.iterdir() if f.is_dir()) == [
        "item_item_name_1",
    ]
    # but is should now be empty as we sent both messages successfully:
    assert not list(f.name for f in (spool_dir / "item_item_name_1").iterdir())


def test_logwatch_spool_path_is_escaped() -> None:
    # item may contain slashes or other stuff, we want to make sure
    # that this is transformed to a single folder name:
    get_spool_path = logwatch_ec.MessageForwarder._get_spool_path
    result = get_spool_path(HostName("some_host_name"), "some/log/path")
    assert result.name == "item_some%2Flog%2Fpath"
    assert result.parent.name == "some_host_name"

    assert get_spool_path(HostName("short"), ".").name == "item_."
    assert get_spool_path(HostName("short"), "..").name == "item_.."


def test_check_logwatch_ec_common_batch_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Multiple logfiles with different batches. All must be remembered as "seen_batches".

    Failing to do so leads to messages being processed multiple times.
    """
    _patch_config_cache(monkeypatch)

    value_store: dict = {}

    _result = list(
        logwatch_ec.check_logwatch_ec_common(
            None,
            DEFAULT_TEST_PARAMETERS,
            {
                None: logwatch_.Section(
                    errors=(),
                    logfiles={
                        "foo": logwatch_.ItemData(attr="", lines={"batch_id_occuring_in_foo": []}),
                        "bar": logwatch_.ItemData(attr="", lines={"batch_id_occuring_in_bar": []}),
                    },
                ),
            },
            logwatch_ec.check_plugin_logwatch_ec_single,
            value_store=value_store,
            message_forwarder=_FakeForwarder(),
        )
    )

    # the value store now needs to report both batches as seen:
    assert value_store["seen_batches"] == ("batch_id_occuring_in_bar", "batch_id_occuring_in_foo")
