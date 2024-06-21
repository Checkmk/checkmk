#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from . import graphs, metrics, perfometers, translations
from ._localize import Title


def entry_point_prefixes() -> Mapping[
    type[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ],
    str,
]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    metric_... = Metric(...)
    translation_... = Translation(...)
    perfometer_... = Perfometer(...)
    perfometer_... = Bidirectional(...)
    perfometer_... = Stacked(...)
    graph_... = Graph(...)
    graph_... = Bidirectional(...)
    """
    return {
        metrics.Metric: "metric_",
        translations.Translation: "translation_",
        perfometers.Perfometer: "perfometer_",
        perfometers.Bidirectional: "perfometer_",
        perfometers.Stacked: "perfometer_",
        graphs.Graph: "graph_",
        graphs.Bidirectional: "graph_",
    }


__all__ = [
    "entry_point_prefixes",
    "graphs",
    "metrics",
    "perfometers",
    "translations",
    "Title",
]
