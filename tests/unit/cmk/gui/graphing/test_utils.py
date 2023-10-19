#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence

import pytest

from tests.unit.cmk.gui.conftest import SetConfig

from cmk.utils.metrics import MetricName

import cmk.gui.graphing._utils as utils
from cmk.gui.config import active_config
from cmk.gui.graphing._expression import CriticalOf, Metric, MetricExpression, WarningOf
from cmk.gui.graphing._utils import (
    _NormalizedPerfData,
    AutomaticDict,
    MetricDefinition,
    TranslationInfo,
)
from cmk.gui.type_defs import Perfdata, PerfDataTuple
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
        ("hi=6 [ihe]", "ter", ([PerfDataTuple("hi", 6, "", None, None, None, None)], "ihe")),
        ("hi=l6 [ihe]", "ter", ([], "ihe")),
        ("hi=6 [ihe]", "ter", ([PerfDataTuple("hi", 6, "", None, None, None, None)], "ihe")),
        (
            "hi=5 no=6",
            "test",
            (
                [
                    PerfDataTuple("hi", 5, "", None, None, None, None),
                    PerfDataTuple("no", 6, "", None, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5;6;7;8;9 'not here'=6;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple("hi", 5, "", 6, 7, 8, 9),
                    PerfDataTuple("not_here", 6, "", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5G;;;; 'not here'=6M;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple("hi", 5, "G", None, None, None, None),
                    PerfDataTuple("not_here", 6, "M", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "11.26=6;;;;",
            "check_mk-local",
            ([PerfDataTuple("11.26", 6, "", None, None, None, None)], "check_mk-local"),
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
            PerfDataTuple("in", 496876.200933, "", None, None, 0, 125000000),
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
            PerfDataTuple("fast", 5, "", 4, 9, 0, 10),
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
def test__normalize_perf_data(
    perf_data: PerfDataTuple, check_command: str, result: tuple[str, _NormalizedPerfData]
) -> None:
    assert utils._normalize_perf_data(perf_data, check_command) == result


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
    perfdata: Perfdata = [PerfDataTuple(n, 0, "", None, None, None, None) for n in metric_names]
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
    perfdata: Perfdata = [PerfDataTuple(n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = utils.translate_metrics(perfdata, "check_command")
    assert [t.id for t in utils.get_graph_templates(translated_metrics)] == graph_ids


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
        [PerfDataTuple("temp", 59.05, "", 85.05, 85.05, None, None)],
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


def test_automatic_dict_append() -> None:
    automatic_dict = AutomaticDict(list_identifier="appended")
    automatic_dict["graph_1"] = {
        "metrics": [
            ("some_metric", "line"),
            ("some_other_metric", "-area"),
        ],
    }
    automatic_dict["graph_2"] = {
        "metrics": [
            ("something", "line"),
        ],
    }
    automatic_dict.append(
        {
            "metrics": [
                ("abc", "line"),
            ],
        }
    )
    automatic_dict.append(
        {
            "metrics": [
                ("xyz", "line"),
            ],
        }
    )
    automatic_dict.append(
        {
            "metrics": [
                ("xyz", "line"),
            ],
        }
    )
    assert dict(automatic_dict) == {
        "appended_0": {
            "metrics": [("abc", "line")],
        },
        "appended_1": {
            "metrics": [("xyz", "line")],
        },
        "graph_1": {
            "metrics": [
                ("some_metric", "line"),
                ("some_other_metric", "-area"),
            ],
        },
        "graph_2": {
            "metrics": [("something", "line")],
        },
    }


@pytest.mark.parametrize(
    "graph_template_registation, expected_graph_template",
    [
        pytest.param(
            utils.RawGraphTemplate(
                metrics=[],
                scalars=["metric", "metric:warn", "metric:crit"],
            ),
            utils.GraphTemplate(
                id="ident",
                title=None,
                scalars=[
                    utils.ScalarDefinition(
                        expression=MetricExpression(Metric("metric")),
                        title="metric",
                    ),
                    utils.ScalarDefinition(
                        expression=MetricExpression(WarningOf(Metric("metric"))),
                        title="Warning",
                    ),
                    utils.ScalarDefinition(
                        expression=MetricExpression(CriticalOf(Metric("metric"))),
                        title="Critical",
                    ),
                ],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[],
            ),
            id="scalar str",
        ),
        pytest.param(
            utils.RawGraphTemplate(
                metrics=[],
                scalars=[("metric", "Title"), ("metric:warn", "Warn"), ("metric:crit", "Crit")],
            ),
            utils.GraphTemplate(
                id="ident",
                title=None,
                scalars=[
                    utils.ScalarDefinition(
                        expression=MetricExpression(Metric("metric")),
                        title="Title",
                    ),
                    utils.ScalarDefinition(
                        expression=MetricExpression(WarningOf(Metric("metric"))),
                        title="Warn",
                    ),
                    utils.ScalarDefinition(
                        expression=MetricExpression(CriticalOf(Metric("metric"))),
                        title="Crit",
                    ),
                ],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[],
            ),
            id="scalar tuple",
        ),
        pytest.param(
            utils.RawGraphTemplate(
                metrics=[("metric", "line")],
            ),
            utils.GraphTemplate(
                id="ident",
                title=None,
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        expression=MetricExpression(Metric("metric")),
                        line_type="line",
                    ),
                ],
            ),
            id="metrics 2-er tuple",
        ),
        pytest.param(
            utils.RawGraphTemplate(
                metrics=[("metric", "line", "Title")],
            ),
            utils.GraphTemplate(
                id="ident",
                title=None,
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        expression=MetricExpression(Metric("metric")),
                        line_type="line",
                        title="Title",
                    ),
                ],
            ),
            id="metrics 3-er tuple",
        ),
    ],
)
def test_graph_template_from_template(
    graph_template_registation: utils.RawGraphTemplate,
    expected_graph_template: utils.GraphTemplate,
) -> None:
    assert (
        utils.GraphTemplate.from_template("ident", graph_template_registation)
        == expected_graph_template
    )
