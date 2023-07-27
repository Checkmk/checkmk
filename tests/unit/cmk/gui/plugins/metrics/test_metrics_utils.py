#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence

import pytest

from tests.unit.cmk.gui.conftest import SetConfig

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.metrics import MetricName

import cmk.gui.metrics as metrics
from cmk.gui.config import active_config
from cmk.gui.plugins.metrics import utils
from cmk.gui.plugins.metrics.utils import (
    hex_color_to_rgb_color,
    NormalizedPerfData,
    TranslationInfo,
)
from cmk.gui.type_defs import HorizontalRule, Perfdata
from cmk.gui.utils.temperate_unit import TemperatureUnit


@pytest.mark.parametrize(
    "data_string, result",
    [
        ("he lo", ["he", "lo"]),
        ("'há li'", ["há li"]),
        ("hé ßß", ["hé", "ßß"]),
    ],
)
def test_split_perf_data(data_string: str, result: Sequence[str]) -> None:
    assert utils._split_perf_data(data_string) == result


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "perf_str, check_command, result",
    [
        ("", None, ([], "")),
        ("hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
        ("hi=l6 [ihe]", "ter", ([], "ihe")),
        ("hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
        (
            "hi=5 no=6",
            "test",
            (
                [
                    ("hi", 5, "", None, None, None, None),
                    ("no", 6, "", None, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5;6;7;8;9 'not here'=6;5.6;;;",
            "test",
            (
                [
                    ("hi", 5, "", 6, 7, 8, 9),
                    ("not_here", 6, "", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5G;;;; 'not here'=6M;5.6;;;",
            "test",
            (
                [
                    ("hi", 5, "G", None, None, None, None),
                    ("not_here", 6, "M", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "11.26=6;;;;",
            "check_mk-local",
            ([("11.26", 6, "", None, None, None, None)], "check_mk-local"),
        ),
    ],
)
def test_parse_perf_data(
    perf_str: str,
    check_command: str | None,
    result: tuple[Perfdata, str],
) -> None:
    assert utils.parse_perf_data(perf_str, check_command) == result


def test_parse_perf_data2(request_context: None, set_config: SetConfig) -> None:
    with pytest.raises(ValueError), set_config(debug=True):
        utils.parse_perf_data("hi ho", None)


@pytest.mark.parametrize(
    "perf_name, check_command, result",
    [
        ("in", "check_mk-lnx_if", {"scale": 8, "name": "if_in_bps", "auto_graph": True}),
        (
            "memused",
            "check_mk-hr_mem",
            {"auto_graph": False, "name": "mem_lnx_total_used", "scale": 1024**2},
        ),
        ("fake", "check_mk-imaginary", {"auto_graph": True, "name": "fake", "scale": 1.0}),
    ],
)
def test_perfvar_translation(perf_name: str, check_command: str, result: TranslationInfo) -> None:
    assert utils.perfvar_translation(perf_name, check_command) == result


@pytest.mark.parametrize(
    ["translations", "expected_result"],
    [
        pytest.param(
            {},
            {},
            id="no translations",
        ),
        pytest.param(
            {MetricName("old_name"): {"name": MetricName("new_name")}},
            {},
            id="no applicable translations",
        ),
        pytest.param(
            {
                MetricName("my_metric"): {"name": MetricName("new_name")},
                MetricName("other_metric"): {"name": MetricName("other_new_name"), "scale": 0.1},
            },
            {"name": MetricName("new_name")},
            id="1-to-1 translations",
        ),
        pytest.param(
            {
                MetricName("~.*my_metric"): {"scale": 5},
                MetricName("other_metric"): {"name": MetricName("other_new_name"), "scale": 0.1},
            },
            {"scale": 5},
            id="regex translations",
        ),
    ],
)
def test_find_matching_translation(
    translations: Mapping[MetricName, utils.CheckMetricEntry],
    expected_result: utils.CheckMetricEntry,
) -> None:
    assert utils.find_matching_translation(MetricName("my_metric"), translations) == expected_result


@pytest.mark.parametrize(
    "perf_data, check_command, result",
    [
        (
            ("in", 496876.200933, "", None, None, 0, 125000000),
            "check_mk-lnx_if",
            (
                "if_in_bps",
                {
                    "orig_name": ["in"],
                    "value": 3975009.607464,
                    "scalar": {"max": 1000000000, "min": 0},
                    "scale": [8],
                    "auto_graph": True,
                },
            ),
        ),
        (
            ("fast", 5, "", 4, 9, 0, 10),
            "check_mk-imaginary",
            (
                "fast",
                {
                    "orig_name": ["fast"],
                    "value": 5.0,
                    "scalar": {"warn": 4.0, "crit": 9.0, "min": 0.0, "max": 10.0},
                    "scale": [1.0],
                    "auto_graph": True,
                },
            ),
        ),
    ],
)
def test_normalize_perf_data(
    perf_data: Perfdata, check_command: str, result: tuple[str, NormalizedPerfData]
) -> None:
    assert utils.normalize_perf_data(perf_data, check_command) == result


@pytest.mark.parametrize(
    ["canonical_name", "current_version", "all_translations", "expected_result"],
    [
        pytest.param(
            MetricName("my_metric"),
            123,
            [
                {
                    MetricName("some_metric_1"): {"scale": 10},
                    MetricName("some_metric_2"): {
                        "scale": 10,
                        "name": MetricName("new_metric_name"),
                    },
                }
            ],
            {MetricName("my_metric")},
            id="no applicable translations",
        ),
        pytest.param(
            MetricName("my_metric"),
            2030020100,
            [
                {
                    MetricName("some_metric_1"): {"scale": 10},
                    MetricName("old_name_1"): {
                        "scale": 10,
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    MetricName("old_name_1"): {
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    MetricName("old_name_2"): {
                        "name": MetricName("my_metric"),
                    },
                    MetricName("irrelevant"): {"name": MetricName("still_irrelevant")},
                },
                {
                    MetricName("old_name_deprecated"): {
                        "name": MetricName("my_metric"),
                        "deprecated": "2.0.0i1",
                    },
                },
            ],
            {
                MetricName("my_metric"),
                MetricName("old_name_1"),
                MetricName("old_name_2"),
            },
            id="some applicable and one deprecated translation",
        ),
        pytest.param(
            MetricName("my_metric"),
            2030020100,
            [
                {
                    MetricName("old_name_1"): {
                        "name": MetricName("my_metric"),
                    },
                },
                {
                    "~.*expr": {
                        "name": MetricName("my_metric"),
                    },
                },
            ],
            {
                MetricName("my_metric"),
                MetricName("old_name_1"),
            },
            id="regex translation",
        ),
    ],
)
def test_reverse_translate_into_all_potentially_relevant_metrics(
    canonical_name: MetricName,
    current_version: int,
    all_translations: Iterable[Mapping[MetricName, utils.CheckMetricEntry]],
    expected_result: frozenset[MetricName],
) -> None:
    assert (
        utils.reverse_translate_into_all_potentially_relevant_metrics(
            canonical_name,
            current_version,
            all_translations,
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "metric_names, check_command, graph_ids",
    [
        (["user", "system", "wait", "util"], "check_mk-kernel_util", ["cpu_utilization_5_util"]),
        (["util1", "util15"], "check_mk-kernel_util", ["util_average_2"]),
        (["util"], "check_mk-kernel_util", ["util_fallback"]),
        (["util"], "check_mk-lxc_container_cpu", ["util_fallback"]),
        (
            ["wait", "util", "user", "system"],
            "check_mk-lxc_container_cpu",
            ["cpu_utilization_5_util"],
        ),
        (["util", "util_average"], "check_mk-kernel_util", ["util_average_1"]),
        (["user", "util_numcpu_as_max"], "check_mk-kernel_util", ["cpu_utilization_numcpus"]),
        (
            ["user", "util"],
            "check_mk-kernel_util",
            ["util_fallback", "METRIC_user"],
        ),  # METRIC_user has no recipe
        (["util"], "check_mk-netapp_api_cpu_utilization", ["cpu_utilization_numcpus"]),
        (["user", "util"], "check_mk-winperf_processor_util", ["cpu_utilization_numcpus"]),
        (["user", "system", "idle", "nice"], "check_mk-kernel_util", ["cpu_utilization_3"]),
        (["user", "system", "idle", "io_wait"], "check_mk-kernel_util", ["cpu_utilization_4"]),
        (["user", "system", "io_wait"], "check_mk-kernel_util", ["cpu_utilization_5"]),
        (
            ["util_average", "util", "wait", "user", "system", "guest"],
            "check_mk-kernel_util",
            ["cpu_utilization_6_guest_util"],
        ),
        (
            ["user", "system", "io_wait", "guest", "steal"],
            "check_mk-statgrab_cpu",
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
        ),
        (["user", "system", "interrupt"], "check_mk-kernel_util", ["cpu_utilization_8"]),
        (
            ["user", "system", "wait", "util", "cpu_entitlement", "cpu_entitlement_util"],
            "check_mk-lparstat_aix_cpu_util",
            ["cpu_utilization_5_util", "cpu_entitlement"],
        ),
        (["ramused", "swapused", "memused"], "check_mk-statgrab_mem", ["ram_swap_used"]),
        (
            [
                "aws_ec2_running_ondemand_instances_total",
                "aws_ec2_running_ondemand_instances_t2.micro",
                "aws_ec2_running_ondemand_instances_t2.nano",
            ],
            "check_mk-aws_ec2_limits",
            ["aws_ec2_running_ondemand_instances"],
        ),
    ],
)
def test_get_graph_templates(
    metric_names: Sequence[str], check_command: str, graph_ids: Sequence[str]
) -> None:
    perfdata: Perfdata = [(n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = utils.translate_metrics(perfdata, check_command)
    assert [t.id for t in utils.get_graph_templates(translated_metrics)] == graph_ids


@pytest.mark.parametrize(
    "metric_names, graph_ids",
    [
        # cpu.py
        pytest.param(
            ["user_time", "children_user_time", "system_time", "children_system_time"],
            ["used_cpu_time"],
            id="used_cpu_time",
        ),
        pytest.param(
            [
                "user_time",
                "children_user_time",
                "system_time",
                "children_system_time",
                "cmk_time_agent",
                "cmk_time_snmp",
                "cmk_time_ds",
            ],
            [
                "METRIC_children_system_time",
                "METRIC_children_user_time",
                "METRIC_cmk_time_agent",
                "METRIC_cmk_time_ds",
                "METRIC_cmk_time_snmp",
                "METRIC_system_time",
                "METRIC_user_time",
            ],
            id="used_cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["user_time", "system_time"],
            ["cpu_time"],
            id="cpu_time",
        ),
        pytest.param(
            ["user_time", "system_time", "children_user_time"],
            ["METRIC_children_user_time", "METRIC_system_time", "METRIC_user_time"],
            id="cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["util", "util_average"],
            ["util_average_1"],
            id="util_average_1",
        ),
        pytest.param(
            [
                "util",
                "util_average",
                "util_average_1",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
                "user",
                "system",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util", "METRIC_util_average_1"],
            id="util_average_1_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "util_average", "util"],
            ["cpu_utilization_simple"],
            id="cpu_utilization_simple",
        ),
        pytest.param(
            [
                "user",
                "system",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_simple_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average"],
            ["cpu_utilization_5"],
            id="cpu_utilization_5",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_5_conflicting_metrics",
        ),
        # cpu_utilization_5_util
        pytest.param(
            ["user", "system", "io_wait", "util_average", "util"],
            ["cpu_utilization_5_util"],
            id="cpu_utilization_5_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_5_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average"],
            ["cpu_utilization_6_steal"],
            id="cpu_utilization_6_steal",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average", "util"],
            ["cpu_utilization_6_steal_util"],
            id="cpu_utilization_6_steal_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "cpu_util_steal"],
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_6_guest",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "cpu_util_steal",
                "util",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "util"],
            ["cpu_utilization_6_guest_util"],
            id="cpu_utilization_6_guest_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "util",
                "cpu_util_steal",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_util_conflicting_metrics",
        ),
        #
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "cpu_util_steal", "util_average"],
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_7",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "cpu_util_steal",
                "util_average",
                "util",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_7_conflicting_metrics",
        ),
        pytest.param(
            ["util"],
            ["util_fallback"],
            id="util_fallback",
        ),
        pytest.param(
            ["util", "util_average", "system", "engine_cpu_util"],
            ["cpu_utilization", "METRIC_system", "METRIC_util_average"],
            id="util_fallback_conflicting_metrics",
        ),
        # fs.py
        pytest.param(
            ["fs_used", "fs_size"],
            ["fs_used"],
            id="fs_used",
        ),
        pytest.param(
            ["fs_used", "fs_size", "reserved"],
            ["METRIC_fs_size", "METRIC_fs_used", "METRIC_reserved"],
            id="fs_used_conflicting_metrics",
        ),
        # mail.py
        pytest.param(
            ["mail_queue_deferred_length", "mail_queue_active_length"],
            ["amount_of_mails_in_queues"],
            id="amount_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_length",
                "mail_queue_active_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_active_length",
                "METRIC_mail_queue_deferred_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_deferred_size", "mail_queue_active_size"],
            ["size_of_mails_in_queues"],
            id="size_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_size",
                "mail_queue_active_size",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_active_size",
                "METRIC_mail_queue_deferred_size",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="size_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_hold_length", "mail_queue_incoming_length", "mail_queue_drop_length"],
            ["amount_of_mails_in_secondary_queues"],
            id="amount_of_mails_in_secondary_queues",
        ),
        pytest.param(
            [
                "mail_queue_hold_length",
                "mail_queue_incoming_length",
                "mail_queue_drop_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_drop_length",
                "METRIC_mail_queue_hold_length",
                "METRIC_mail_queue_incoming_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_secondary_queues_conflicting_metrics",
        ),
        # storage.py
        pytest.param(
            ["mem_used", "swap_used"],
            ["ram_swap_used"],
            id="ram_swap_used",
        ),
        pytest.param(
            ["mem_used", "swap_used", "swap_total"],
            ["METRIC_mem_used", "METRIC_swap_total", "METRIC_swap_used"],
            id="ram_swap_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive"],
            ["active_and_inactive_memory"],
            id="active_and_inactive_memory",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive", "mem_lnx_active_anon"],
            [
                "METRIC_mem_lnx_active",
                "METRIC_mem_lnx_active_anon",
                "METRIC_mem_lnx_inactive",
            ],
            id="active_and_inactive_memory_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used"],
            ["ram_used"],
            id="ram_used",
        ),
        pytest.param(
            ["mem_used", "swap_used"],
            ["ram_swap_used"],
            id="ram_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap"],
            ["heap_and_non_heap_memory"],
            id="heap_and_non_heap_memory",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap", "mem_heap_committed", "mem_nonheap_committed"],
            ["heap_memory_usage", "non-heap_memory_usage"],
            id="heap_and_non_heap_memory_conflicting_metrics",
        ),
    ],
)
def test_conflicting_metrics(metric_names: Sequence[str], graph_ids: Sequence[str]) -> None:
    # Hard to find all avail metric names of a check plugin.
    # We test conflicting metrics as following:
    # 1. write test for expected metric names of a graph template if it has "conflicting_metrics"
    # 2. use metric names from (1) and conflicting metrics
    perfdata: Perfdata = [(n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = utils.translate_metrics(perfdata, "check_command")
    assert [t.id for t in utils.get_graph_templates(translated_metrics)] == graph_ids


def test_replace_expression() -> None:
    perfdata: Perfdata = [(n, len(n), "", 120, 240, 0, 25) for n in ["load1"]]
    translated_metrics = utils.translate_metrics(perfdata, "check_mk-cpu.loads")
    assert (
        utils.replace_expressions("CPU Load - %(load1:max@count) CPU Cores", translated_metrics)
        == "CPU Load - 25  CPU Cores"
    )


@pytest.mark.parametrize(
    "text, out",
    [
        ("fs_size", ("fs_size", None, None)),
        ("if_in_octets,8,*@bits/s", ("if_in_octets,8,*", "bits/s", None)),
        ("fs_size,fs_used,-#e3fff9", ("fs_size,fs_used,-", None, "e3fff9")),
        ("fs_size,fs_used,-@kb#e3fff9", ("fs_size,fs_used,-", "kb", "e3fff9")),
    ],
)
def test_extract_rpn(text: str, out: tuple[str, str | None, str | None]) -> None:
    assert utils.split_expression(text) == out


def test_evaluate() -> None:
    perfdata: Perfdata = [(n, len(n), "", 120, 240, 0, 24) for n in ["in", "out"]]
    translated_metrics = utils.translate_metrics(perfdata, "check_mk-openvpn_clients")
    assert utils.evaluate("if_in_octets,8,*@bits/s", translated_metrics) == (
        16.0,
        utils.unit_info["bits/s"],
        "#00e060",
    )
    perfdata = [(n, len(n), "", None, None, None, None) for n in ["/", "fs_size"]]
    translated_metrics = utils.translate_metrics(perfdata, "check_mk-df")
    assert utils.evaluate("fs_size,fs_used,-#e3fff9", translated_metrics) == (
        6291456,
        utils.unit_info["bytes"],
        "#e3fff9",
    )

    # This is a terrible metric from Nagios plugins. Test is for survival instead of correctness
    # The unit "percent" is lost on the way. Fixing this would imply also figuring out how to represent
    # graphs for active-icmp check when host has multiple addresses.
    assert utils.evaluate(
        "127.0.0.1pl",
        utils.translate_metrics(
            utils.parse_perf_data("127.0.0.1pl=5%;80;100;;")[0], "check_mk_active-icmp"
        ),
    ) == (5, utils.unit_info[""], "#cc00ff")

    # Here the user has a metrics that represent subnets, but the values look like floats
    # Test that evaluation recognizes the metric from the perf data
    assert utils.evaluate(
        "10.172",
        utils.translate_metrics(utils.parse_perf_data("10.172=6")[0], "check_mk-local"),
    ) == (6, utils.unit_info[""], "#cc00ff")


@pytest.mark.parametrize(
    "perf_data, expression, check_command, expected_result",
    [
        pytest.param(
            "util=605;;;0;100",
            "util,100,MAX",
            "check_mk-bintec_cpu",
            605.0,
        ),
        pytest.param(
            "user=4.600208;;;; system=1.570093;;;; io_wait=0.149533;;;;",
            "user,system,io_wait,+,+,100,MAX",
            "check_mk-kernel_util",
            100.0,
        ),
        pytest.param(
            "user=101.000000;;;; system=0.100000;;;; io_wait=0.010000;;;;",
            "user,system,io_wait,+,+,100,MAX",
            "check_mk-kernel_util",
            101.11,
        ),
    ],
)
def test_evaluate_cpu_utilization(
    perf_data: str, expression: str, check_command: str, expected_result: float
) -> None:
    """Clamping to upper value.

    Technically, the percent values for CPU Utilization should always be between 0 and 100. In
    practice, these values can be above 100. This was observed for docker (SUP-13161). In this
    case, it is sensible to extend the graph. This behaviour would be a sensible default, but
    currently using our `stack_resolver` is the only.

    This test provides a sanity check that the stack_resolver clamps the values in the way it
    should.
    """
    # Assemble
    assert utils.metric_info, "Global variable is empty/has not been initialized."
    assert utils.graph_info, "Global variable is empty/has not been initialized."
    perf_data_parsed, check_command = utils.parse_perf_data(perf_data, check_command)
    translated_metrics = utils.translate_metrics(perf_data_parsed, check_command)
    # Act
    result = utils.evaluate(expression, translated_metrics)
    # Assert
    assert result[0] == expected_result


def test_stack_resolver_str_to_nested() -> None:
    def apply_operator(op: str, f: Sequence[object], s: Sequence[object]) -> Sequence[object]:
        return (op, [f, s])

    assert utils.stack_resolver(
        ["1", "2", "+"],
        lambda x: x == "+",
        apply_operator,
        lambda x: x,
    ) == ("+", ["1", "2"])


def test_stack_resolver_str_to_str() -> None:
    assert (
        utils.stack_resolver(
            ["1", "2", "+"],
            lambda x: x == "+",
            lambda op, f, s: " ".join((op, f, s)),
            lambda x: x,
        )
        == "+ 1 2"
    )


@pytest.mark.parametrize(
    "elements, is_operator, apply_operator, apply_element, result",
    [
        pytest.param(
            ["1", "2", "+"],
            lambda x: x == "+",
            lambda op, f, s: f + s,
            int,
            3,
            id="Reduce",
        ),
        pytest.param(
            ["1", "2", "+", "3", "+"],
            lambda x: x == "+",
            lambda op, f, s: f + s,
            int,
            6,
            id="Reduce coupled",
        ),
    ],
)
def test_stack_resolver_str_to_int(
    elements: list[str],
    is_operator: Callable[[str], bool],
    apply_operator: Callable[[str, int, int], int],
    apply_element: Callable[[str], int],
    result: int,
) -> None:
    assert utils.stack_resolver(elements, is_operator, apply_operator, apply_element) == result


def test_stack_resolver_exception() -> None:
    def apply_operator(op: str, f: int, s: int) -> int:
        return f + s

    with pytest.raises(MKGeneralException, match="too many operands left"):
        utils.stack_resolver(
            "1 2 3 +".split(),
            lambda x: x == "+",
            apply_operator,
            int,
        )


def test_stack_resolver_exception_missing_operator_arguments() -> None:
    def apply_operator(op: str, f: int, s: int) -> int:
        return f + s

    with pytest.raises(
        MKGeneralException, match="Syntax error in expression '3, T': too few operands"
    ):
        utils.stack_resolver(
            "3 T".split(),
            lambda x: x == "T",
            apply_operator,
            int,
        )


def test_graph_titles() -> None:
    graphs_without_title = sorted(
        graph_id
        for graph_id, graph_info in utils.graph_templates_internal().items()
        if not graph_info.title
    )
    assert (
        not graphs_without_title
    ), f"Please provide titles for the following graphs: {', '.join(graphs_without_title)}"


@pytest.mark.parametrize(
    "perf_string, result",
    [
        pytest.param(
            "one=5;;;; power=5;;;; output=5;;;;",
            [],
            id="Unknown thresholds from check",
        ),
        pytest.param(
            "one=5;7;6;; power=5;9;10;; output=5;2;3;;",
            [
                (7.0, "7.00", "#ffd000", "Warning"),
                (10.0, "10.0 W", "#ff3232", "Critical power"),
                (-2.0, "-2.00", "#ffd000", "Warning output"),
            ],
            id="Thresholds present",
        ),
    ],
)
def test_horizontal_rules_from_thresholds(
    perf_string: str, result: Sequence[HorizontalRule]
) -> None:
    assert (
        utils.horizontal_rules_from_thresholds(
            [
                "one:warn",
                ("power:crit", "Critical power"),
                ("output:warn,-1,*", "Warning output"),
            ],
            metrics.translate_perf_data(perf_string),
        )
        == result
    )


@pytest.mark.parametrize(
    "hex_color, expected_rgb",
    [
        ("#112233", (17, 34, 51)),
        ("#123", (17, 34, 51)),
    ],
)
def test_hex_color_to_rgb_color(hex_color: str, expected_rgb: tuple[int, int, int]) -> None:
    assert hex_color_to_rgb_color(hex_color) == expected_rgb


@pytest.mark.parametrize(
    ["idx", "total"],
    [
        (-1, -1),
        (-1, 0),
        (0, 0),
        (1, 0),
    ],
)
def test_indexed_color_raises(idx: int, total: int) -> None:
    with pytest.raises(MKGeneralException):
        utils.indexed_color(idx, total)


@pytest.mark.parametrize(
    "idx",
    range(0, utils._COLOR_WHEEL_SIZE),
)
def test_indexed_color_uses_color_wheel_first(idx: int) -> None:
    assert "/" in utils.indexed_color(idx, utils._COLOR_WHEEL_SIZE)


@pytest.mark.parametrize(
    ["idx", "total"],
    [
        (89, 143),
        (55, 55),
        (355, 552),
        (90, 100),
        (67, 89),
        (95, 452),
        (111, 222),
    ],
)
def test_indexed_color_sanity(idx: int, total: int) -> None:
    color = utils.indexed_color(idx, total)
    assert "/" not in color
    r, g, b = utils.hex_color_to_rgb_color(color)
    if r == g == b:
        assert all(100 <= component <= 200 for component in (r, g, b))
    else:
        assert all(60 <= component <= 230 for component in (r, g, b) if component)


@pytest.mark.parametrize(
    ["default_temperature_unit", "expected_value", "expected_scalars"],
    [
        pytest.param(
            TemperatureUnit.CELSIUS,
            59.05,
            {"warn": 85.05, "crit": 85.05},
            id="no unit conversion",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            138.29,
            {"warn": 185.09, "crit": 185.09},
            id="with unit conversion",
        ),
    ],
)
def test_translate_metrics(
    default_temperature_unit: TemperatureUnit,
    expected_value: float,
    expected_scalars: Mapping[str, float],
) -> None:
    active_config.default_temperature_unit = default_temperature_unit.value
    translated_metric = utils.translate_metrics(
        [("temp", 59.05, "", 85.05, 85.05, None, None)],
        "check_mk-lnx_thermal",
    )["temp"]
    assert translated_metric["value"] == expected_value
    assert translated_metric["scalar"] == expected_scalars


@pytest.mark.parametrize(
    ["all_translations", "check_command", "expected_result"],
    [
        pytest.param(
            {},
            "check_mk-x",
            None,
            id="no matching entry",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            "check_mk-x",
            {MetricName("old"): {"name": MetricName("new")}},
            id="standard check",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            "check_mk-mgmt_x",
            {MetricName("old"): {"name": MetricName("new")}},
            id="management board, fallback to standard check",
        ),
        pytest.param(
            {
                "check_mk_x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-mgmt_x": {MetricName("old"): {"scale": 3}},
            },
            "check_mk-mgmt_x",
            {MetricName("old"): {"scale": 3}},
            id="management board, explicit entry",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            None,
            None,
            id="no check command",
        ),
    ],
)
def test_lookup_metric_translations_for_check_command(
    all_translations: Mapping[str, Mapping[MetricName, utils.CheckMetricEntry]],
    check_command: str | None,
    expected_result: Mapping[MetricName, utils.CheckMetricEntry] | None,
) -> None:
    assert (
        utils.lookup_metric_translations_for_check_command(
            all_translations,
            check_command,
        )
        == expected_result
    )
