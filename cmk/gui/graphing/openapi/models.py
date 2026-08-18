#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Annotated, Literal, Self

from annotated_types import Interval
from pydantic import Json

from cmk.graphing_engine import Unit
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel
from cmk.gui.type_defs import IconNames
from cmk.shared_typing.cmk_time_series_graph import UnitFormat

from .._engine_discovery import BuiltGraph, DiscoveredGraphs
from .._engine_dispatch import serialize_graphs
from .._engine_unit_format import notation_name, precision_kind

type ApiConsolidation = Literal["min", "max", "avg"]

# How a combined graph folds the same metric across its matched services: aggregate
# (sum/average/min/max) or show each service separately (lines/stacked).
type ApiCombinationMode = Literal["lines", "stacked", "sum", "average", "min", "max"]


@api_model
class ApiPrecision:
    type: Literal["auto", "strict"] = api_field(
        description="The precision rounding mode.", example="auto"
    )
    digits: Annotated[int, Interval(ge=0)] = api_field(
        description="The number of digits.", example=2
    )


@api_model
class ApiUnitFormat:
    notation: Literal[
        "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
    ] = api_field(description="The unit notation.", example="decimal")
    symbol: str = api_field(description="The unit symbol.", example="B")
    precision: ApiPrecision = api_field(description="The unit precision.")
    convertible: bool = api_field(description="Whether the unit is auto-convertible.", example=True)

    @classmethod
    def from_shared(cls, unit_format: UnitFormat) -> Self:
        return cls(
            notation=unit_format.notation,
            symbol=unit_format.symbol,
            precision=ApiPrecision(
                type=unit_format.precision.type, digits=unit_format.precision.digits
            ),
            convertible=True if unit_format.convertible is None else unit_format.convertible,
        )

    @classmethod
    def from_engine_unit(cls, unit: Unit) -> Self:
        # TODO: The engine ``Unit`` has no convertibility concept, so default to convertible
        #  (matches the shared unit-format default).
        return cls(
            notation=notation_name(unit),
            symbol=unit.notation.symbol,
            precision=ApiPrecision(type=precision_kind(unit), digits=unit.precision.digits),
            convertible=True,
        )


@api_model
class ApiTimeRange:
    start: int = api_field(description="The start timestamp (epoch seconds).", example=1700000000)
    end: int = api_field(description="The end timestamp (epoch seconds).", example=1700003600)
    step: int = api_field(description="The step size in seconds.", example=60)


@api_model
class ApiMetricAttribute:
    kind: str = api_field(
        description="The kind of source the attribute describes, e.g. the resource the metric was "
        "collected from, the scope that collected it or the data point itself.",
        example="resource",
    )
    name: str = api_field(description="The attribute name.", example="service.name")
    value: str = api_field(description="The attribute value.", example="checkout")


@api_model
class ApiMetricMetadata:
    name: str = api_field(
        description="The stable structural identifier of the metric.",
        example="<implementation detail>",
    )
    title: str = api_field(
        description="The metric title.",
        example="CPU utilization",
    )
    unit: ApiUnitFormat = api_field(description="The metric unit.")
    color: str = api_field(description="The metric color.", example="#ff0000")
    attributes: list[ApiMetricAttribute] = api_field(
        description="The attributes of the series the metric was fetched from. Empty for a metric "
        "without any, e.g. one fetched from an RRD.",
        default_factory=list,
        example=[],
    )


@api_model
class ApiMetricRender:
    stack: str | None = api_field(
        description="The stack group id. None = line; unique id = area; shared id = stacked.",
        example="stack-0",
    )
    inverse: bool = api_field(description="Whether the metric is mirrored.", example=False)
    hidden: bool = api_field(
        description="Whether the metric is drawn (used for stack baselines).", example=False
    )


@api_model
class ApiMetric:
    metadata: ApiMetricMetadata = api_field(description="The metric metadata.")
    render: ApiMetricRender = api_field(description="The metric rendering options.")
    data_points: list[float | None] | None = api_field(
        description="The data points. None when unfetched; an array (possibly with nulls) otherwise.",
        example=[1.0, 2.5, None, 3.0],
    )


@api_model
class ApiHorizontalLine:
    name: str = api_field(
        description="The stable structural identifier of the horizontal line.",
        example="<implementation detail>",
    )
    title: str = api_field(
        description="The localized line title, for the legend.",
        example="Warning",
    )
    value: float = api_field(description="The horizontal line value.", example=80.0)
    unit: ApiUnitFormat = api_field(
        description="The unit the line value is rendered with - that of the metric it bounds."
    )
    color: str = api_field(description="The horizontal line color.", example="#ffcc00")


@api_model
class ApiExplicitRange:
    min: float = api_field(description="The lower edge of the axis.", example=0.0)
    max: float = api_field(description="The upper edge of the axis.", example=100.0)


@api_model
class ApiYAxis:
    """The axis a graph names for itself."""

    unit: ApiUnitFormat | ApiOmitted = api_field(
        description=(
            "The unit to label the axis in. Absent to label it in the unit of the metrics the "
            "graph draws."
        ),
        default_factory=ApiOmitted,
    )
    explicit_range: ApiExplicitRange | ApiOmitted = api_field(
        description=(
            "The edges the axis is fixed to. Absent to scale it to the values that are drawn."
        ),
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_built(cls, built: BuiltGraph) -> Self | None:
        """The axis the graph names, or None when it names none at all."""
        bounds = built.y_axis_bounds()
        if built.y_axis_unit is None and bounds is None:
            return None
        return cls(
            unit=(
                ApiOmitted()
                if built.y_axis_unit is None
                else ApiUnitFormat.from_shared(built.y_axis_unit)
            ),
            explicit_range=(
                ApiOmitted() if bounds is None else ApiExplicitRange(min=bounds[0], max=bounds[1])
            ),
        )


@api_model
class ApiDiscoveredGraph:
    """A discovered data-less graph definition."""

    internal: str = api_field(
        description=(
            "The self-contained graph definition needed to fetch the data, as JSON. Pass it "
            "to the fetch_data action unchanged."
        ),
        example="<implementation detail>",
    )
    title: str = api_field(
        description="The localized graph title, for the graph header.",
        example="CPU utilization",
    )
    name: str = api_field(
        description=(
            "The graph's own name, as the rendering component identifies it by. Unlike the "
            "title it is not localized."
        ),
        example="cpu_utilization",
    )
    y_axis: ApiYAxis | None = api_field(
        description=(
            "The value axis this graph names for itself, e.g. the unit and range a custom graph "
            "was configured with. Null when the graph names none, which leaves the whole axis to "
            "be derived from the metrics it draws."
        )
    )
    add_to_specification: dict[str, object] | None = api_field(
        description=(
            "The specification identifying this one graph, to be passed to the add_to_visual and "
            "add_to_container actions unchanged. Null for graph kinds that offer no add-to action."
        ),
        example={
            "graph_type": "template",
            "site": "mysite",
            "host_name": "my-host",
            "service_description": "CPU load",
            "graph_id": "cpu_load",
        },
    )

    @classmethod
    def from_built(cls, built: BuiltGraph) -> Self:
        return cls(
            internal=json.dumps(serialize_graphs([built.graph])),
            title=built.graph.title,
            name=built.graph.name,
            y_axis=ApiYAxis.from_built(built),
            add_to_specification=(
                None if built.specification is None else built.specification.model_dump()
            ),
        )


@api_model
class GraphsDiscoverResponse:
    """The shared response of the graph discovery endpoints."""

    graphs: list[ApiDiscoveredGraph] = api_field(
        description="The data-less graph definitions. Empty when nothing matched.",
    )
    no_data_message: str | None = api_field(
        description=(
            "A human-readable explanation of why no graphs are available (an expected empty "
            "state, e.g. a filter matching no monitored data), or null when graphs were found."
        ),
        example="There is no registered metric named 'cpu_utilization'.",
    )

    @classmethod
    def from_discovered(cls, discovered: DiscoveredGraphs) -> Self:
        return cls(
            graphs=[ApiDiscoveredGraph.from_built(built) for built in discovered.graphs],
            no_data_message=discovered.no_data_message,
        )


@api_model
class MetricNameMappingResponse:
    metric_names: dict[str, str] = api_field(
        description=(
            "The canonical metric name each of the service's raw perf-data names is known by, "
            "keyed by the raw name. A name no plug-in renames maps to itself, so every name the "
            "service reports has an entry. Empty when the host or service is not monitored, or "
            "when it reports no perf data at all."
        ),
        example={"wait": "io_wait", "user": "user"},
    )


@api_model
class GraphFetchRequest:
    internal: Annotated[Mapping[str, object], Json] = api_field(
        description="The self-contained graph definition needed to recompute the data, as JSON.",
        example="<implementation detail>",
    )
    requested_time_range: ApiTimeRange = api_field(
        description="The time range (and step) to fetch data for. The returned range may differ.",
    )
    consolidation_function: ApiConsolidation = api_field(
        description="The consolidation function to use for RRD data.", example="avg"
    )
    combination_mode: ApiCombinationMode | None = api_field(
        description=(
            "How to combine the same metric across services for a combined graph: aggregate "
            "(sum/average/min/max) or show each service separately (lines/stacked). Defaults "
            "to sum. Ignored by other graph types."
        ),
        example="sum",
        default=None,
    )


@api_model
class GraphFetchResponse:
    title: str = api_field(
        description=(
            "The localized graph title, for the graph header. Any title expression a plug-in wrote "
            "(e.g. the number of CPU cores) is substituted from the fetched data, which is why the "
            "header takes its title from here rather than from the definition."
        ),
        example="CPU load - 8 CPU cores",
    )
    time_range: ApiTimeRange = api_field(
        description="The actual time range the returned data covers (may differ from the request).",
    )
    metrics: list[ApiMetric] = api_field(
        description="The evaluated series in render order (stack members, then lines)."
    )
    horizontal_lines: list[ApiHorizontalLine] = api_field(
        description="The horizontal (threshold) lines."
    )
    warnings: list[str] = api_field(
        description=(
            "Non-fatal warnings about the fetched data, e.g. a query whose result was truncated "
            "because it hit the maximum number of time series. Empty when there is nothing to warn "
            "about."
        ),
        example=[],
    )
    errors: list[str] = api_field(
        description=(
            "Non-fatal errors that occurred while fetching individual metrics; the rest of the "
            "graph is still returned. Empty on success."
        ),
        example=[],
    )


BurgerMenuActionType = Literal["add_to_container", "add_to_visual", "export"]


@api_model
class BurgerMenuAction:
    id: BurgerMenuActionType = api_field(description="The action type.", example="add_to_container")
    parameters: list[str] = api_field(
        description="The action parameters.", example=["graph_collection", "my_fancy_collection"]
    )


@api_model
class BurgerMenuItem:
    label: str = api_field(
        example="Add to custom graph",
        description="The label of the action.",
    )
    ariaLabel: str = api_field(
        example="Add to custom graph",
        description="The aria-label of the action.",
    )
    icon: IconNames = api_field(
        example="plus",
        description="The icon of the action.",
    )
    action: BurgerMenuAction = api_field(
        example={
            "id": "add_to_container",
            "parameters": ["graph_collection", "my_fancy_collection"],
        },
        description="The action of the menu item.",
    )


@api_model
class BurgerMenuGroup:
    heading: str = api_field(
        example="Add to",
        description="The heading of the group.",
    )
    items: list[BurgerMenuItem] = api_field(
        description="A list of action items.",
    )


@api_model
class BurgerMenuCollection(DomainObjectCollectionModel):
    domainType: Literal["burger_menu"] = api_field(
        description="The domain type of the objects in the collection.",
        example="burger_menu",
    )
    value: list[BurgerMenuGroup] = api_field(
        description="A list of BurgerMenuGroup objects.",
    )


@api_model
class GraphInternalRepresentation:
    internal: str = api_field(
        description="The internal representation of the graph",
        example="<implementation detail>",
    )


@api_model
class AddToRequest:
    # Not a GraphInternalRepresentation: the add-to backends store the legacy specification and
    # replay it when the target is rendered, so the engine's graph definition is of no use here.
    specification: dict[str, object] = api_field(
        example={
            "graph_type": "template",
            "site": "mysite",
            "host_name": "my-host",
            "service_description": "CPU load",
            "graph_id": "cpu_load",
        },
        description="The specification of the graph to add, as returned by the discover actions.",
    )
    family: str = api_field(
        example="graph_collection",
        description="The family collection where to add the graph to.",
    )
    id: str = api_field(
        example="my_graph_collection",
        description="The id of the collection to add the graph to.",
    )


@api_model
class AddToContainerRequest(AddToRequest):
    # A container may store what a graph is made of rather than how it was requested, so the built
    # graph travels along and the target takes whichever of the two it holds.
    internal: Annotated[Mapping[str, object], Json] = api_field(
        description="The built graph, as returned by the discover actions.",
        example="<implementation detail>",
    )


@api_model
class AddToContainerResponse:
    sidebar_reload_required: bool = api_field(
        description=(
            "Whether the sidebar has to be reloaded. Adding to a container the user does not own "
            "clones it first, which makes a new page appear in the sidebar."
        ),
        example=False,
    )


@api_model
class ExportRequest:
    # Not a GraphInternalRepresentation: the export pages render from the legacy specification, the
    # same one the add-to actions replay. The consolidation function and the range are the ones the
    # graph currently shows - unlike the add-to actions, the export does honour them.
    specification: dict[str, object] = api_field(
        example={
            "graph_type": "template",
            "site": "mysite",
            "host_name": "my-host",
            "service_description": "CPU load",
            "graph_id": "cpu_load",
        },
        description=(
            "The specification of the graph to export, as returned by the discover actions."
        ),
    )
    target: Literal["graph_export", "graph_image"] = api_field(
        example="graph_image",
        description="How to export the graph",
    )
    consolidation_function: ApiConsolidation = api_field(
        description="The consolidation function the graph is displayed with.",
        example="avg",
        default="max",
    )
    time_start: int | None = api_field(
        description="Start of the displayed range, as a UNIX timestamp. 25 hours ago when omitted.",
        example=1781524800,
        default=None,
    )
    time_end: int | None = api_field(
        description="End of the displayed range, as a UNIX timestamp. Now when omitted.",
        example=1781528400,
        default=None,
    )


@api_model
class ExportResponse:
    download_url: str = api_field(
        description=(
            "The URL the browser has to follow to receive the exported file. It answers with a "
            "Content-Disposition attachment, so following it downloads the file rather than "
            "leaving the graph."
        ),
        example="graph_image.py?request=%7B%22specification%22%3A+%7B%7D%7D",
    )
