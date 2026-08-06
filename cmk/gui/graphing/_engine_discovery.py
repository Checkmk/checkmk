#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Graph discovery: resolving a graph specification to the data-less engine graphs it matches.
# Both the REST discovery endpoints and the dashboard graph widgets go through here, so the
# interactive and the shared (token-authenticated) dashboard resolve the same graphs.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine import HostName, ServiceName
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.i18n import _

from ._engine_dispatch import BuiltGraph
from ._engine_plugins import registered_graphs, registered_metrics, registered_translations
from ._engine_rrd import EngineRRDFetchMetricNames
from ._engine_template_graphs import build_template_graphs


@dataclass(frozen=True)
class DiscoveredGraphs:
    """The data-less graphs a specification matched.

    An empty match is an expected state (nothing monitored, no matching template, ...), not a
    failure: `no_data_message` then explains it in the caller's language. Failures - a dead
    monitoring core, a broken specification - are raised instead.
    """

    graphs: Sequence[BuiltGraph]
    no_data_message: str | None

    @classmethod
    def found(cls, graphs: Sequence[BuiltGraph]) -> DiscoveredGraphs:
        return cls(graphs=graphs, no_data_message=None)

    @classmethod
    def nothing(cls, no_data_message: str) -> DiscoveredGraphs:
        return cls(graphs=[], no_data_message=no_data_message)


def discover_template_graphs(
    specification: TemplateGraphSpecification, *, debug: bool
) -> DiscoveredGraphs:
    """Discover the template graphs of a service."""
    try:
        graphs = build_template_graphs(
            specification,
            registered_graphs=registered_graphs(),
            registered_metrics=registered_metrics(),
            fetch_metric_names=EngineRRDFetchMetricNames(
                host_name=HostName(specification.host_name),
                service_name=ServiceName(specification.service_description),
                debug=debug,
                site_id=specification.site,
                registered_translations=registered_translations(),
            ),
        )
    except MKMissingDataError as exc:
        return DiscoveredGraphs.nothing(str(exc))

    if not graphs:
        return DiscoveredGraphs.nothing(
            _("The service '%(service)s' of host '%(host)s' has no matching template graphs.")
            % {
                "service": specification.service_description,
                "host": specification.host_name,
            }
        )
    return DiscoveredGraphs.found(graphs)
