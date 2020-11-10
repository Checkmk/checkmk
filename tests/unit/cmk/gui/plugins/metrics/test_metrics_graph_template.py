#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
import cmk.gui.plugins.metrics.graph_templates as gt
import cmk.gui.metrics as metrics


@pytest.mark.parametrize("expression, enforced_consolidation_function, result", [
    ('user', 'max', [('user', 'max')]),
    ('user.min', None, [('user', 'min')]),
    ('user.min,sys,+', None, [('user', 'min'), ('sys', None), ('+', None)]),
    ('user.min,sys.max,+', None, [('user', 'min'), ('sys', 'max'), ('+', None)]),
])
def test_rpn_consolidation(expression, enforced_consolidation_function, result):
    assert list(gt.iter_rpn_expression(expression, enforced_consolidation_function)) == result


@pytest.mark.parametrize("expression, enforced_consolidation_function", [('user.min', 'max'),
                                                                         ('user.min,sys,+', 'avg')])
def test_rpn_consolidation_exception(expression, enforced_consolidation_function):
    with pytest.raises(gt.MKGeneralException):
        list(gt.iter_rpn_expression(expression, enforced_consolidation_function))


@pytest.mark.parametrize("expression, result", [
    ('fs_size,fs_used,-', ('operator', '-', [('rrd', '', '', '', 'fs_size', None, 1048576),
                                             ('rrd', '', '', '', '_', None, 1048576)])),
    ('fs_growth.min,0,MIN,-1,*', ('operator', '*', [
        ('operator', 'MIN', [('rrd', '', '', '', 'growth', 'min', 12.136296296296296),
                             ('constant', 0.0)]),
        ('constant', -1.0),
    ])),
])
def test_rpn_stack(expression, result):
    translated_metrics = metrics.translate_perf_data(
        '/=163651.992188;;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;', "check_mk-df")
    lq_row = {"site": "", "host_name": "", "service_description": ""}
    assert gt.metric_expression_to_graph_recipe_expression(expression, translated_metrics, lq_row,
                                                           None) == result


def test_create_graph_recipe_from_template():

    metrics.fixup_unit_info()
    import cmk.gui.plugins.metrics.utils as utils
    graph_template = utils.graph_info['fs_used']
    translated_metrics = metrics.translate_perf_data(
        '/=163651.992188;;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;', "check_mk-df")
    lq_row = {"site": "", "host_name": "", "service_description": ""}

    assert gt.create_graph_recipe_from_template(graph_template, translated_metrics, lq_row) == {
        'title': 'Used filesystem space',
        'metrics': [{
            'unit': 'bytes',
            'color': '#00ffc6',
            'title': 'Used filesystem space',
            'line_type': 'area',
            'expression': ('rrd', '', '', '', '_', 'max', 1048576)
        }, {
            'unit': 'bytes',
            'color': '#e3fff9',
            'title': 'Free space',
            'line_type': 'stack',
            'expression': ('operator', '-', [('rrd', '', '', '', 'fs_size', 'max', 1048576),
                                             ('rrd', '', '', '', '_', 'max', 1048576)])
        }, {
            'unit': 'bytes',
            'color': '#006040',
            'title': 'Filesystem size',
            'line_type': 'line',
            'expression': ('rrd', '', '', '', 'fs_size', 'max', 1048576)
        }],
        'unit': 'bytes',
        'explicit_vertical_range': (0.0, None),
        'horizontal_rules': [],
        'omit_zero_metrics': False,
        'consolidation_function': 'max'
    }


@pytest.mark.parametrize("perf_string, result", [
    pytest.param('one=5;;;; power=5;;;; output=5;;;;', [], id="Unknown thresholds from check"),
    pytest.param('one=5;7;6;; power=5;9;10;; output=5;2;3;;', [
        (7.0, '7.00', '#ffff00', 'Warning'),
        (10.0, '10.0 W', '#ff0000', 'Critical power'),
        (-2.0, '-2.00', '#ffff00', 'Warning output'),
    ],
                 id="Thresholds present"),
])
def test_horizontal_rules_from_thresholds(perf_string, result):
    thresholds = [
        "one:warn",
        ("power:crit", "Critical power"),
        ("output:warn,-1,*", "Warning output"),
    ]
    translated_metrics = metrics.translate_perf_data(perf_string)
    assert gt._horizontal_rules_from_thresholds(thresholds, translated_metrics) == result


@pytest.mark.parametrize("expression, perf_string, check_command, result_color", [
    ('load15', 'load1=0.38;40;80;0;8 load5=0.62;40;80;0;8 load15=0.68;40;80;0;8',
     'check_mk-cpu.loads', '#2c5766'),
    ('test', 'test=5;5;10;0;20', 'check_mk-local', "#cc00ff"),
])
def test_metric_unit_color(expression, perf_string, check_command, result_color):
    metrics.fixup_unit_info()
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    reference = {
        "color": result_color,
        "unit": translated_metrics.get(expression, {}).get('unit', {}).get('id', '')
    }
    assert gt.metric_unit_color(expression, translated_metrics, ['test']) == reference


@pytest.mark.parametrize("expression, perf_string, check_command", [
    ('test', '', 'check_mk-local'),
])
def test_metric_unit_color_skip(expression, perf_string, check_command):
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    assert gt.metric_unit_color(expression, translated_metrics, ['test']) is None


@pytest.mark.parametrize("metric, perf_string, check_command", [
    ('level,altitude,+', 'test=5;5;10;0;20', 'check_mk-local'),
])
def test_metric_unit_color_exception(metric, perf_string, check_command):
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    with pytest.raises(gt.MKGeneralException):
        gt.metric_unit_color(metric, translated_metrics, ['test'])
