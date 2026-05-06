#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.ccc.hostaddress import HostName
from cmk.ec import forwarder as ec_forwarder_patch_target
from cmk.ec.forwarder import ForwardedResult, MessageForwarder
from cmk.ec.syslog import SyslogMessage
from cmk.logwatch.config import (
    ParameterLogwatchEc,
    ParameterLogwatchRules,
    set_global_state,
    unset_global_state,
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

DEFAULT_TEST_PARAMETERS = ParameterLogwatchEc(
    {
        **logwatch_ec.CHECK_DEFAULT_PARAMETERS,
        "service_level": 10,
        "host_name": "test-host",
        "is_preview": False,
    }
)


class _LogwatchConfigDummy:
    def __init__(
        self, ec_rules: Sequence[ParameterLogwatchEc] = (), tmp_path: Path = Path("/dev/null")
    ) -> None:
        self._ec_rules = ec_rules
        self.base_spool_path = tmp_path / "base_spool"
        self.omd_root = tmp_path / "omd_root"
        self.msg_dir = tmp_path / "msg_dir"
        self.debug = False

    def logwatch_rules_all(
        self, *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]:
        return ()

    def logwatch_ec_all(self, host_name: str) -> Sequence[ParameterLogwatchEc]:
        return self._ec_rules


@contextmanager
def _logwatch_state(config: _LogwatchConfigDummy) -> Iterator[None]:
    set_global_state(config)
    try:
        yield
    finally:
        unset_global_state()


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (_STRING_TABLE_NO_MESSAGES, [], []),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant", service_level=10, is_preview=False, separate_checks=True
                )
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
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*"],
                )
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*"],
                    separate_checks=True,
                ),
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
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*"],
                    separate_checks=False,
                ),
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*"],
                ),
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=["log1"],
                    separate_checks=True,
                    method="pass me on!",
                    facility=0,
                    monitor_logfilelist=False,
                    monitor_logfile_access_state=0,
                    logwatch_reclassify=False,
                    some_other_key="I should be discarded!",  # type: ignore[typeddict-unknown-key]
                ),
            ],
            [
                Service(
                    item="log1",
                    parameters={
                        "expected_logfiles": ["log1"],
                        "method": "pass me on!",
                        "facility": 0,
                        "monitor_logfilelist": False,
                        "monitor_logfile_access_state": 0,
                        "logwatch_reclassify": False,
                    },
                ),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_single(
    info: StringTable,
    fwd_rule: Sequence[ParameterLogwatchEc],
    expected_result: DiscoveryResult,
) -> None:
    parsed = parse_logwatch(info)

    with _logwatch_state(_LogwatchConfigDummy(fwd_rule)):
        actual_result = sorted(
            logwatch_ec.discover_single(parsed, {"host_name": "test-host"}),
            key=lambda s: s.item or "",
        )
        assert actual_result == expected_result


@pytest.mark.parametrize(
    "info, fwd_rule, expected_result",
    [
        (_STRING_TABLE_NO_MESSAGES, [], []),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant", service_level=10, is_preview=False, separate_checks=True
                )
            ],
            [],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    separate_checks=False,
                )
            ],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2", "log4", "log5"]}),
            ],
        ),
        (
            _STRING_TABLE_NO_MESSAGES,
            [
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*[12]"],
                    separate_checks=False,
                )
            ],
            [
                Service(parameters={"expected_logfiles": ["log1", "log2"]}),
            ],
        ),
    ],
)
def test_logwatch_ec_inventory_groups(
    info: StringTable,
    fwd_rule: Sequence[ParameterLogwatchEc],
    expected_result: DiscoveryResult,
) -> None:
    parsed = parse_logwatch(info)

    with _logwatch_state(_LogwatchConfigDummy(fwd_rule)):
        actual_result = list(logwatch_ec.discover_group(parsed, {"host_name": "test-host"}))
        assert actual_result == expected_result


class _FakeForwarder(MessageForwarder):
    def __init__(self) -> None:
        pass

    @property
    def debug(self) -> bool:
        return False

    def __call__(
        self,
        method: str | tuple,
        messages: Sequence[SyslogMessage],
        timestamp: float,
    ) -> ForwardedResult:
        return ForwardedResult(num_forwarded=len(messages))


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
                "is_preview": False,
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
    params: ParameterLogwatchEc,
    parsed: logwatch_.ClusterSection,
    expected_result: CheckResult,
) -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
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


def test_check_logwatch_ec_common_single_node_log_missing() -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
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
                    "is_preview": False,
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
) -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
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
            ParameterLogwatchEc(
                {
                    "facility": 17,  # default to "local1"
                    "method": "",  # local site
                    "monitor_logfilelist": False,
                    "monitor_logfile_access_state": 2,
                    "expected_logfiles": ["log4"],
                    "service_level": 10,
                    "host_name": "test-host",
                    "is_preview": False,
                }
            ),
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
    params: ParameterLogwatchEc,
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


def test_check_logwatch_ec_common_multiple_nodes_item_partially_missing() -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
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


def test_check_logwatch_ec_common_multiple_nodes_logfile_missing() -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
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
                    "is_preview": False,
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


def test_check_logwatch_ec_common_spool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = _LogwatchConfigDummy(tmp_path=tmp_path)
    with _logwatch_state(config):
        monkeypatch.setattr(ec_forwarder_patch_target, "_MAX_SPOOL_SIZE", 32)
        assert list(
            logwatch_ec.check_logwatch_ec_common(
                "log1",
                ParameterLogwatchEc({**DEFAULT_TEST_PARAMETERS, "method": "spool:"}),
                {
                    "node1": SECTION1,
                },
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store={},
                message_forwarder=MessageForwarder(
                    "log1",
                    HostName("test-host"),
                    base_spool_path=config.base_spool_path,
                    omd_root=config.omd_root,
                    debug=False,
                ),
            )
        ) == [
            Result(state=State.OK, summary="Forwarded 3 messages from log1"),
            Metric("messages", 3.0),
        ]
        assert len(list(Path(config.omd_root, "var/mkeventd/spool").iterdir())) == 3


def test_check_logwatch_ec_common_batch_stored() -> None:
    """Multiple logfiles with different batches. All must be remembered as "seen_batches".

    Failing to do so leads to messages being processed multiple times.
    """
    with _logwatch_state(_LogwatchConfigDummy()):
        value_store: dict = {}

        _result = list(
            logwatch_ec.check_logwatch_ec_common(
                None,
                DEFAULT_TEST_PARAMETERS,
                {
                    None: logwatch_.Section(
                        errors=(),
                        logfiles={
                            "foo": logwatch_.ItemData(
                                attr="", lines={"batch_id_occuring_in_foo": []}
                            ),
                            "bar": logwatch_.ItemData(
                                attr="", lines={"batch_id_occuring_in_bar": []}
                            ),
                        },
                    ),
                },
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store=value_store,
                message_forwarder=_FakeForwarder(),
            )
        )

        # the value store now needs to report both batches as seen:
        assert value_store["seen_batches"] == (
            "batch_id_occuring_in_bar",
            "batch_id_occuring_in_foo",
        )


class _RaisingForwarder(MessageForwarder):
    """Forwarder that fails the test if called — used to assert forwarding is skipped."""

    def __init__(self) -> None:
        pass

    @property
    def debug(self) -> bool:
        return False

    def __call__(
        self,
        method: str | tuple,
        messages: Sequence[SyslogMessage],
        timestamp: float,
    ) -> ForwardedResult:
        raise AssertionError("message_forwarder must not be called in preview mode")


def test_check_logwatch_ec_common_preview_does_not_forward() -> None:
    """In preview mode, messages are not forwarded and a summary of what would be sent is shown."""
    with _logwatch_state(_LogwatchConfigDummy()):
        result = list(
            logwatch_ec.check_logwatch_ec_common(
                "log1",
                ParameterLogwatchEc({**DEFAULT_TEST_PARAMETERS, "is_preview": True}),
                {"node1": parse_logwatch(_STRING_TABLE_MESSAGES_LOG1)},
                logwatch_ec.check_plugin_logwatch_ec_single,
                value_store={},
                message_forwarder=_RaisingForwarder(),
            )
        )
    assert result == [
        Result(state=State.OK, summary="Preview: 2 messages would be forwarded from log1"),
    ]
