#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import translations as translations_api
from cmk.gui.graphing._from_api import graphs_from_api, metrics_from_api
from cmk.gui.graphing._graph_templates import get_graph_plugin_from_id
from cmk.gui.graphing._legacy import check_metrics
from cmk.gui.graphing._metrics import get_metric_spec
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.graphing_main import _add_graphing_plugins
from cmk.gui.unit_formatter import StrictPrecision


def test_add_graphing_plugins_registers_every_supported_plugin_kind() -> None:
    """Test the graphing plug-in loader/registrar with a synthetic
    `DiscoveredPlugins` collection.

    Covering one entry of every kind the registrar knows about (`Metric`, `Graph`, `Translation`).
    The test confirms that the loader-side bridge from the public `cmk.graphing.v1` API into
    the internal `metrics_from_api` / `graphs_from_api` / `check_metrics` registries works end-to-end
    and preserves the relevant attributes (title, unit, color, lines, translations)
    """
    test_metric_1 = metrics_api.Metric(
        name="syntest_count_first",
        title=graphing_api.Title("Synthetic test count (first)"),
        unit=metrics_api.Unit(
            metrics_api.DecimalNotation(""),
            metrics_api.StrictPrecision(2),
        ),
        color=metrics_api.Color.PURPLE,
    )
    test_metric_2 = metrics_api.Metric(
        name="syntest_count_second",
        title=graphing_api.Title("Synthetic test count (second)"),
        unit=metrics_api.Unit(
            metrics_api.DecimalNotation(""),
            metrics_api.StrictPrecision(2),
        ),
        color=metrics_api.Color.BLUE,
    )
    test_graph = graphs_api.Graph(
        name="syntest_counts",
        title=graphing_api.Title("Synthetic test counts"),
        simple_lines=[
            "syntest_count_first",
            "syntest_count_second",
            metrics_api.WarningOf("syntest_count_first"),
            metrics_api.CriticalOf("syntest_count_first"),
        ],
    )
    test_translation = translations_api.Translation(
        name="syntest_translation",
        check_commands=[translations_api.PassiveCheck("syntest_check")],
        translations={
            "raw_value": translations_api.RenameToAndScaleBy("renamed_value", 0.01),
            "raw_rpm": translations_api.RenameTo("fan_speed"),
        },
    )
    _add_graphing_plugins(
        DiscoveredPlugins(
            errors=[],
            plugins={
                PluginLocation("syntest", "metric_1"): test_metric_1,
                PluginLocation("syntest", "metric_2"): test_metric_2,
                PluginLocation("syntest", "graph"): test_graph,
                PluginLocation("syntest", "translation"): test_translation,
            },
        )
    )

    registered_metric_1 = get_metric_spec("syntest_count_first", metrics_from_api)
    assert registered_metric_1.name == "syntest_count_first"
    assert registered_metric_1.title == "Synthetic test count (first)"
    assert registered_metric_1.unit_spec == ConvertibleUnitSpecification(
        notation=DecimalNotation(symbol=""),
        precision=StrictPrecision(digits=2),
    )
    # Color goes through a palette mapping; just check it's a non-empty string.
    assert registered_metric_1.color

    registered_metric_2 = get_metric_spec("syntest_count_second", metrics_from_api)
    assert registered_metric_2.name == "syntest_count_second"
    assert registered_metric_2.title == "Synthetic test count (second)"

    assert check_metrics["check_mk-syntest_check"] == {
        "raw_value": {"name": "renamed_value", "scale": 0.01},
        "raw_rpm": {"name": "fan_speed"},
    }

    assert get_graph_plugin_from_id(graphs_from_api, "syntest_counts") == graphs_api.Graph(
        name="syntest_counts",
        title=graphing_api.Title("Synthetic test counts"),
        simple_lines=[
            "syntest_count_first",
            "syntest_count_second",
            metrics_api.WarningOf("syntest_count_first"),
            metrics_api.CriticalOf("syntest_count_first"),
        ],
    )
