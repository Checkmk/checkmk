#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.metrics as metrics
import cmk.gui.plugins.metrics.graph_templates as gt
from cmk.gui.plugins.metrics.utils import (
    GraphRecipe,
    GraphTemplate,
    TranslatedMetrics,
    unit_info,
    UnitConverter,
)


@pytest.mark.parametrize(
    "expression, enforced_consolidation_function, result",
    [
        ("user", "max", [("user", "max")]),
        ("user.min", None, [("user", "min")]),
        ("user.min,sys,+", None, [("user", "min"), ("sys", None), ("+", None)]),
        ("user.min,sys.max,+", None, [("user", "min"), ("sys", "max"), ("+", None)]),
    ],
)
def test_rpn_consolidation(  # type:ignore[no-untyped-def]
    expression, enforced_consolidation_function, result
) -> None:
    assert list(gt.iter_rpn_expression(expression, enforced_consolidation_function)) == result


@pytest.mark.parametrize(
    "expression, enforced_consolidation_function", [("user.min", "max"), ("user.min,sys,+", "avg")]
)
def test_rpn_consolidation_exception(  # type:ignore[no-untyped-def]
    expression, enforced_consolidation_function
) -> None:
    with pytest.raises(gt.MKGeneralException):
        list(gt.iter_rpn_expression(expression, enforced_consolidation_function))


@pytest.mark.parametrize(
    "expression, result",
    [
        (
            "fs_size,fs_used,-",
            (
                "operator",
                "-",
                [
                    ("rrd", "", "", "", "fs_size", None, 1048576),
                    ("rrd", "", "", "", "_", None, 1048576),
                ],
            ),
        ),
        (
            "fs_growth.min,0,MIN,-1,*",
            (
                "operator",
                "*",
                [
                    (
                        "operator",
                        "MIN",
                        [
                            ("rrd", "", "", "", "growth", "min", 12.136296296296296),
                            ("constant", 0.0),
                        ],
                    ),
                    ("constant", -1.0),
                ],
            ),
        ),
    ],
)
def test_rpn_stack(expression, result) -> None:  # type:ignore[no-untyped-def]
    translated_metrics = metrics.translate_perf_data(
        "/=163651.992188;;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;", "check_mk-df"
    )
    lq_row = {"site": "", "host_name": "", "service_description": ""}
    assert (
        gt.metric_expression_to_graph_recipe_expression(
            expression, translated_metrics, lq_row, None
        )
        == result
    )


def test_create_graph_recipe_from_template() -> None:

    metrics.fixup_unit_info()
    graph_template = GraphTemplate(
        {
            "metrics": [
                ("fs_used", "area"),
                ("fs_size,fs_used,-#e3fff9", "stack", "Free space"),
                ("fs_size", "line"),
            ],
            "scalars": [
                "fs_used:warn",
                "fs_used:crit",
            ],
            "range": (0, "fs_used:max"),
            "conflicting_metrics": ["fs_free"],
        }
    )
    translated_metrics = metrics.translate_perf_data(
        "/=163651.992188;;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;", "check_mk-df"
    )
    lq_row = {"site": "", "host_name": "", "service_description": ""}

    assert gt.create_graph_recipe_from_template(graph_template, translated_metrics, lq_row) == {
        "title": "Used space",
        "metrics": [
            {
                "unit": "bytes",
                "color": "#00ffc6",
                "title": "Used space",
                "line_type": "area",
                "expression": ("rrd", "", "", "", "_", "max", 1048576),
            },
            {
                "unit": "bytes",
                "color": "#e3fff9",
                "title": "Free space",
                "line_type": "stack",
                "expression": (
                    "operator",
                    "-",
                    [
                        ("rrd", "", "", "", "fs_size", "max", 1048576),
                        ("rrd", "", "", "", "_", "max", 1048576),
                    ],
                ),
            },
            {
                "unit": "bytes",
                "color": "#006040",
                "title": "Total size",
                "line_type": "line",
                "expression": ("rrd", "", "", "", "fs_size", "max", 1048576),
            },
        ],
        "unit": "bytes",
        "explicit_vertical_range": (0.0, None),
        "horizontal_rules": [],
        "omit_zero_metrics": False,
        "source_unit": "bytes",
        "consolidation_function": "max",
    }


@pytest.mark.parametrize(
    "expression, perf_string, check_command, result_color",
    [
        (
            "load15",
            "load1=0.38;40;80;0;8 load5=0.62;40;80;0;8 load15=0.68;40;80;0;8",
            "check_mk-cpu.loads",
            "#2c5766",
        ),
        ("test", "test=5;5;10;0;20", "check_mk-local", "#cc00ff"),
    ],
)
def test_metric_unit_color(  # type:ignore[no-untyped-def]
    expression, perf_string, check_command, result_color
) -> None:
    metrics.fixup_unit_info()
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    translated_metric = translated_metrics.get(expression)
    assert translated_metric is not None
    unit = translated_metric.get("unit")
    assert unit is not None
    unit_id = unit.get("id")
    reference = {
        "color": result_color,
        "unit": unit_id,
    }
    assert gt.metric_unit_color(expression, translated_metrics, ["test"]) == reference


@pytest.mark.parametrize(
    "expression, perf_string, check_command",
    [
        ("test", "", "check_mk-local"),
    ],
)
def test_metric_unit_color_skip(  # type:ignore[no-untyped-def]
    expression, perf_string, check_command
) -> None:
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    assert gt.metric_unit_color(expression, translated_metrics, ["test"]) is None


@pytest.mark.parametrize(
    "metric, perf_string, check_command",
    [
        ("level,altitude,+", "test=5;5;10;0;20", "check_mk-local"),
    ],
)
def test_metric_unit_color_exception(  # type:ignore[no-untyped-def]
    metric, perf_string, check_command
) -> None:
    translated_metrics = metrics.translate_perf_data(perf_string, check_command)
    with pytest.raises(gt.MKGeneralException):
        gt.metric_unit_color(metric, translated_metrics, ["test"])


@pytest.mark.parametrize(
    "from_unit, to_unit, unconverted_metrics, expected_metrics",
    [
        (
            "c",
            "f",
            {
                "temp": {
                    "title": "Temperature",
                    "value": 54.05,
                    "scalar": {"warn": 65.05, "crit": 75.05},
                    "unit": {"title": "Degree Celsius"},
                }
            },
            {
                "temp": {
                    "title": "Temperature",
                    "scalar": {"crit": 167.09, "warn": 149.09},
                    "unit": {"id": "f"},
                    "value": 129.29,
                },
            },
        ),
        (
            "c",
            "f",
            {"temp": {"title": "Temperature"}},
            {"temp": {"title": "Temperature"}},
        ),
    ],
)
def test_get_converted_metrics(
    from_unit: str,
    to_unit: str,
    unconverted_metrics: TranslatedMetrics,
    expected_metrics: TranslatedMetrics,
) -> None:
    # Filling "unit" in expected_metrics at runtime because `unit_info` is not populated yet when
    # the parameters are created
    for current_metric in expected_metrics.values():
        unit_id = current_metric.get("unit", {}).get("id")
        if unit_id is None:
            continue
        current_metric["unit"] = unit_info[unit_id]

    converter = UnitConverter(from_unit, to_unit)
    assert gt.get_converted_metrics(converter, unconverted_metrics) == expected_metrics


CREATE_GRAPH_RECIPE_METRICS: TranslatedMetrics = {
    "temp": {
        "orig_name": ["temp"],
        "value": 51.05,
        "scalar": {"warn": 65.05, "crit": 75.05},
        "scale": [1.0],
        "auto_graph": True,
        "title": "Temperature",
        "unit": {
            "title": "Degree Celsius",
            "symbol": "°C",
            "id": "c",
            "description": "Degree Celsius",
            "render": lambda x: f"{x} °C",
            "js_render": "v => cmk.number_format.drop_dotzero(v) + ' °C'",
        },
        "color": "#ffa000",
    }
}
CREATE_GRAPH_RECIPE_ROW = {
    "site": "heute",
    "service_perf_data": "temp=51.05;65.05;75.05;;",
    "service_metrics": ["temp"],
    "service_check_command": "check_mk-lnx_thermal",
    "host_name": "heute",
    "service_description": "Temperature Zone 1",
}
CREATE_GRAPH_RECIPE_BASE_GRAPH_TEMPLATE = {
    "title": "Temperature",
    "metrics": [("temp", "area")],
    "scalars": ["temp:warn", "temp:crit"],
    "id": "temperature",
}
CREATE_GRAPH_RECIPE_EXPECTED_RECIPE_WITH_CONVERSION = {
    "title": "Temperature",
    "metrics": [
        {
            "title": "Temperature",
            "line_type": "area",
            "expression": (
                "rrd",
                "heute",
                "heute",
                "Temperature Zone 1",
                "temp",
                "max",
                1.0,
            ),
            "color": "#ffa000",
            "unit": "f",
        }
    ],
    "unit": "f",
    "explicit_vertical_range": (None, None),
    "horizontal_rules": [
        (149.09, "149.09 °F", "#ffd000", "Warning"),
        (167.09, "167.09 °F", "#ff3232", "Critical"),
    ],
    "omit_zero_metrics": False,
    "consolidation_function": "max",
    "source_unit": "c",
}
CREATE_GRAPH_RECIPE_EXPECTED_RECIPE_WITHOUT_CONVERSION = {
    "title": "Temperature",
    "metrics": [
        {
            "title": "Temperature",
            "line_type": "area",
            "expression": (
                "rrd",
                "heute",
                "heute",
                "Temperature Zone 1",
                "temp",
                "max",
                1.0,
            ),
            "color": "#ffa000",
            "unit": "c",
        }
    ],
    "unit": "c",
    "explicit_vertical_range": (None, None),
    "horizontal_rules": [
        (65.05, "65.05 °C", "#ffd000", "Warning"),
        (75.05, "75.05 °C", "#ff3232", "Critical"),
    ],
    "omit_zero_metrics": False,
    "consolidation_function": "max",
    "source_unit": "c",
}


@pytest.mark.parametrize(
    "graph_template, expected_recipe",
    [
        (
            CREATE_GRAPH_RECIPE_BASE_GRAPH_TEMPLATE | {"convert_unit_to": "f"},
            CREATE_GRAPH_RECIPE_EXPECTED_RECIPE_WITH_CONVERSION,
        ),
        (
            CREATE_GRAPH_RECIPE_BASE_GRAPH_TEMPLATE,
            CREATE_GRAPH_RECIPE_EXPECTED_RECIPE_WITHOUT_CONVERSION,
        ),
        (
            CREATE_GRAPH_RECIPE_BASE_GRAPH_TEMPLATE | {"convert_unit_to": "not_existing_unit"},
            CREATE_GRAPH_RECIPE_EXPECTED_RECIPE_WITHOUT_CONVERSION,
        ),
    ],
)
def test_create_graph_recipe_from_template_unit_conversion(
    graph_template: GraphTemplate, expected_recipe: GraphRecipe
) -> None:
    assert (
        gt.create_graph_recipe_from_template(
            graph_template, CREATE_GRAPH_RECIPE_METRICS, CREATE_GRAPH_RECIPE_ROW
        )
        == expected_recipe
    )
