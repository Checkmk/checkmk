#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple, List
import pytest  # type: ignore[import]

import cmk.gui.config
import cmk.utils.version
from cmk.gui.plugins.metrics import utils


@pytest.mark.parametrize("data_string, result", [
    ("he lo", ["he", "lo"]),
    ("'há li'", ["há li"]),
    (u"hé ßß", [u"hé", u"ßß"]),
])
def test_split_perf_data(data_string, result):
    assert utils._split_perf_data(data_string) == result


@pytest.mark.parametrize("perf_str, check_command, result", [
    ("", None, ([], "")),
    ("hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
    (u"hi=l6 [ihe]", "ter", ([], "ihe")),
    (u"hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
    ("hi=5 no=6", "test", ([
        ("hi", 5, u"", None, None, None, None),
        ("no", 6, u"", None, None, None, None),
    ], "test")),
    ("hi=5;6;7;8;9 'not here'=6;5.6;;;", "test", ([
        ("hi", 5, u"", 6, 7, 8, 9),
        ("not_here", 6, u"", 5.6, None, None, None),
    ], "test")),
    ("hi=5G;;;; 'not here'=6M;5.6;;;", "test", ([
        ("hi", 5, u"G", None, None, None, None),
        ("not_here", 6, u"M", 5.6, None, None, None),
    ], "test")),
])
def test_parse_perf_data(perf_str, check_command, result):
    assert utils.parse_perf_data(perf_str, check_command) == result


def test_parse_perf_data2(monkeypatch):
    with pytest.raises(ValueError):
        monkeypatch.setattr(cmk.gui.config, "debug", True)
        utils.parse_perf_data("hi ho", None)


@pytest.mark.parametrize("perf_name, check_command, result", [
    ("in", "check_mk-lnx_if", {
        "scale": 8,
        "name": "if_in_bps",
        "auto_graph": True
    }),
    ("memused", "check_mk-hr_mem", {
        "auto_graph": False,
        "name": "mem_lnx_total_used",
        "scale": 1024**2
    }),
    ("fake", "check_mk-imaginary", {
        "auto_graph": True,
        "name": "fake",
        "scale": 1.0
    }),
])
def test_perfvar_translation(perf_name, check_command, result):
    assert utils.perfvar_translation(perf_name, check_command) == result


@pytest.mark.parametrize("perf_data, check_command, result", [
    (("in", 496876.200933, "", None, None, 0, 125000000), 'check_mk-lnx_if', ('if_in_bps', {
        "orig_name": ["in"],
        "value": 3975009.607464,
        "scalar": {
            "max": 1000000000,
            "min": 0
        },
        "scale": [8],
        "auto_graph": True,
    })),
    (("fast", 5, "", 4, 9, 0, 10), 'check_mk-imaginary', ('fast', {
        "orig_name": ["fast"],
        "value": 5.0,
        "scalar": {
            "warn": 4.0,
            "crit": 9.0,
            "min": 0.0,
            "max": 10.0
        },
        "scale": [1.0],
        "auto_graph": True,
    })),
])
def test_normalize_perf_data(perf_data, check_command, result):
    assert utils.normalize_perf_data(perf_data, check_command) == result


@pytest.mark.parametrize("canonical_name, perf_data_names, on_cmk_version", [
    ('user', [('user', 1)], "2.0.0"),
    ('io_wait', [('io_wait', 1), ('wait', 1)], "1.6.0p18"),
    ('mem_used', [('mem_used', 1), ('memory', 1048576), ('memory_used', 1), ('memused', 1),
                  ('ramused', 1048576), ('usage', 1)], "2.0.0"),
    ('mem_used', [('mem_used', 1)], "2.1.0b2"),
    ('mem_lnx_shmem', [('mem_lnx_shmem', 1), ('shared', 1048576), ('shmem', 1)], "2.0.0i1"),
    ('mem_lnx_shmem', [('mem_lnx_shmem', 1), ('shmem', 1)], "2.1.0b2"),
])
def test_reverse_translation_metric_name(monkeypatch, canonical_name, perf_data_names,
                                         on_cmk_version):
    utils.reverse_translate_metric_name.clear()  # clear memoized cache, to incorporate version
    monkeypatch.setattr(cmk.utils.version, "__version__", on_cmk_version)
    assert utils.reverse_translate_metric_name(canonical_name) == perf_data_names


@pytest.mark.parametrize(
    "metric_names, check_command, graph_ids",
    [
        ([u'user', u'system', u'wait', u'util'], 'check_mk-kernel_util', ['cpu_utilization_5_util'
                                                                         ]),
        ([u'util1', u'util15'], None, ['util_average_2']),
        ([u'util'], None, ['util_fallback']),
        ([u'util'], "check_mk-lxc_container_cpu", ['util_fallback']),
        ([u'wait', u'util', 'user', 'system'
         ], 'check_mk-lxc_container_cpu', ['cpu_utilization_5_util']),
        ([u'util', u'util_average'], None, ['util_average_1']),
        ([u'user', u'util_numcpu_as_max'], None, ['cpu_utilization_numcpus']),
        ([u'user', u'util'], None, ['util_fallback', 'METRIC_user']),  # METRIC_user has no recipe
        ([u'util'], 'check_mk-netapp_api_cpu_utilization', ['cpu_utilization_numcpus']),
        ([u'user', u'util'], 'check_mk-winperf_processor_util', ['cpu_utilization_numcpus']),
        ([u'user', u'system', u'idle', u'nice'], None, ['cpu_utilization_3']),
        ([u'user', u'system', u'idle', u'io_wait'], None, ['cpu_utilization_4']),
        ([u'user', u'system', u'io_wait'], None, ['cpu_utilization_5']),
        (['util_average', 'util', 'wait', 'user', 'system', 'guest'
         ], "check_mk-kernel_util", ['util_average_1', 'cpu_utilization_6_guest_util']),
        ([u'user', u'system', u'io_wait', 'guest', 'steal'
         ], 'check_mk-statgrab_cpu', ['cpu_utilization_7']),
        ([u'user', u'system', u'interrupt'], None, ['cpu_utilization_8']),
        ([u'user', u'system', u'wait', u'util', u'cpu_entitlement', u'cpu_entitlement_util'
         ], 'check_mk-lparstat_aix_cpu_util', ['cpu_utilization_5_util', 'cpu_entitlement']),
        ([u'ramused', u'swapused', u'memused'], 'check_mk-statgrab_mem', ['ram_swap_used']),
        ([
            u'aws_ec2_running_ondemand_instances_total',
            u'aws_ec2_running_ondemand_instances_t2.micro',
            u'aws_ec2_running_ondemand_instances_t2.nano'
        ], 'check_mk-aws_ec2_limits', ['aws_ec2_running_ondemand_instances'])
    ])
def test_get_graph_templates(load_plugins, metric_names, check_command, graph_ids):
    perfdata: List[Tuple] = [(n, 0, u'', None, None, None, None) for n in metric_names]
    translated_metrics = utils.translate_metrics(perfdata, check_command)
    templates = utils.get_graph_templates(translated_metrics)
    assert set(graph_ids) == set(t['id'] for t in templates)


def test_replace_expression():
    perfdata: List[Tuple] = [(n, len(n), u'', 120, 240, 0, 25) for n in ['load1']]
    translated_metrics = utils.translate_metrics(perfdata, 'check_mk-cpu.loads')
    assert utils.replace_expressions("CPU Load - %(load1:max@count) CPU Cores",
                                     translated_metrics) == 'CPU Load - 25  CPU Cores'


@pytest.mark.parametrize("text, out", [
    ('fs_size', ('fs_size', None, None)),
    ('if_in_octets,8,*@bits/s', ('if_in_octets,8,*', 'bits/s', None)),
    ('fs_size,fs_used,-#e3fff9', ('fs_size,fs_used,-', None, 'e3fff9')),
    ('fs_size,fs_used,-@kb#e3fff9', ('fs_size,fs_used,-', 'kb', 'e3fff9')),
])
def test_extract_rpn(text, out):
    assert utils.split_expression(text) == out


def test_evaluate():
    perfdata: List[Tuple] = [(n, len(n), u'', 120, 240, 0, 24) for n in ['in', 'out']]
    translated_metrics = utils.translate_metrics(perfdata, 'check_mk-openvpn_clients')
    assert utils.evaluate("if_in_octets,8,*@bits/s",
                          translated_metrics) == (16.0, utils.unit_info['bits/s'], '#00e060')
    perfdata = [(n, len(n), u'', None, None, None, None) for n in ['/', 'fs_size']]
    translated_metrics = utils.translate_metrics(perfdata, 'check_mk-df')
    assert utils.evaluate("fs_size,fs_used,-#e3fff9",
                          translated_metrics) == (6291456, utils.unit_info['bytes'], '#e3fff9')


@pytest.mark.parametrize("elements, is_operator, apply_operator, apply_element, result", [
    pytest.param(["1", "2", "+"],
                 lambda x: x == "+",
                 lambda op, f, s: (op, [f, s]),
                 lambda x: x, ("+", ["1", "2"]),
                 id="Nest expression"),
    pytest.param(["1", "2", "+"],
                 lambda x: x == "+",
                 lambda op, f, s: " ".join((op, f, s)),
                 lambda x: x,
                 "+ 1 2",
                 id="Contanate elements"),
    pytest.param(["1", "2", "+"], lambda x: x == "+", lambda op, f, s: f + s, int, 3, id="Reduce"),
    pytest.param(["1", "2", "+", "3", "+"],
                 lambda x: x == "+",
                 lambda op, f, s: f + s,
                 int,
                 6,
                 id="Reduce coupled"),
])
def test_stack_resolver(elements, is_operator, apply_operator, apply_element, result):
    assert utils.stack_resolver(elements, is_operator, apply_operator, apply_element) == result


def test_stack_resolver_exception():
    with pytest.raises(utils.MKGeneralException, match="too many operands left"):
        utils.stack_resolver('1 2 3 +'.split(), lambda x: x == "+", lambda op, f, s: f + s, int)


def test_stack_resolver_exception_missing_operator_arguments():
    with pytest.raises(utils.MKGeneralException,
                       match="Syntax error in expression '3, T': too few operands"):
        utils.stack_resolver('3 T'.split(), lambda x: x == "T", lambda op, f, s: f + s, int)
