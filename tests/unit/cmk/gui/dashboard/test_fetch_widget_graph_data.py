#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the token-authenticated graph widget data fetch."""

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import cast, Literal

import pytest

from cmk.ccc.user import UserId
from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    Graph,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.gui.config import active_config
from cmk.gui.dashboard.api.fetch_widget_graph_data import (
    fetch_widget_graph_data_v1,
    WidgetGraphFetchRequest,
)
from cmk.gui.dashboard.api.model.widget_source import SavedWidgetContent
from cmk.gui.dashboard.dashlet.dashlets.graph import TemplateGraphDashlet
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.graphing import (
    BuiltGraph,
    DiscoveredGraphs,
    EvaluatedGraphs,
    FetchDiagnostics,
)
from cmk.gui.graphing.openapi import fetch_graph_data as fetch_graph_data_module
from cmk.gui.graphing.openapi.models import ApiTimeRange
from cmk.gui.logged_in import user
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentDownloadToken, AuthToken, TokenId
from cmk.gui.type_defs import UserSpec
from tests.testlib.unit.gui.users import create_and_destroy_user
from tests.unit.cmk.gui.helpers.dashboard_widget_resolution_test_helper import (
    api_context,
    dashboard_token,
    impersonating,
)

_WIDGET_ID = "test_dashboard-0"

_REQUEST = WidgetGraphFetchRequest(
    source=SavedWidgetContent(type="saved", widget_id=_WIDGET_ID),
    requested_time_range=ApiTimeRange(start=0, end=60, step=10),
    consolidation_function="avg",
)


def _built() -> BuiltGraph:
    return BuiltGraph(graph=Graph(name="g", title="t", kind="template"), specification=None)


def _agent_download_token() -> AuthToken:
    return AuthToken(
        issuer=UserId("cmkadmin"),
        issued_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        valid_until=None,
        token_id=TokenId("the-token"),
        details=AgentDownloadToken(),
    )


def _graph_widget(widget_type: str = "pnpgraph", **extra: object) -> DashletConfig:
    widget: dict[str, object] = {
        "type": widget_type,
        "timerange": "25h",
        # An explicit site keeps the widget from resolving one over livestatus while it is
        # constructed.
        "context": {
            "site": {"site": "NO_SITE"},
            "host": {"host": "my-host"},
            "service": {"service": "CPU utilization"},
        },
        "single_infos": [],
        **extra,
    }
    return cast(DashletConfig, widget)


def _discovering(monkeypatch: pytest.MonkeyPatch, graphs: Sequence[BuiltGraph]) -> None:
    monkeypatch.setattr(
        TemplateGraphDashlet,
        "discover_graphs",
        lambda _self, **_kwargs: DiscoveredGraphs(graphs=graphs, no_data_message=None),
    )


def _celsius_graph(_graphs: Sequence[Graph], _options: Mapping[str, object]) -> EvaluatedGraphs:
    """One 20 °C data point, so a Fahrenheit reader must get 68.0 and a "°F" symbol."""
    unit = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    return EvaluatedGraphs(
        graphs=[
            EvaluatedGraph(
                name="g",
                title="t",
                vertical_range=None,
                stacks=[],
                lines=[
                    EvaluatedLine(
                        curve=EvaluatedCurve(
                            id="c",
                            attributes=CurveAttributes(
                                title="Temperature", unit=unit, color="#123456"
                            ),
                            value=20.0,
                            time_series=TimeSeries(
                                time_range=TimeRange(start=0, end=30, step=10),
                                values=[20.0],
                            ),
                            source_id=None,
                        ),
                        inverse=False,
                    )
                ],
            )
        ],
        diagnostics=FetchDiagnostics(),
    )


def test_fetch_with_a_token_of_another_kind_is_401() -> None:
    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(api_context(_agent_download_token()), _REQUEST)
    assert exc_info.value.code == 401


def test_fetch_with_a_disabled_dashboard_token_is_401() -> None:
    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(api_context(dashboard_token(disabled=True)), _REQUEST)
    assert exc_info.value.code == 401


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_a_widget_without_a_discovered_graph_is_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [])

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(api_context(dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_evaluates_the_widgets_discovered_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    # An empty graph has no metrics, so this runs end to end without a livestatus fixture.
    impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [_built()])

    response = fetch_widget_graph_data_v1(api_context(dashboard_token()), _REQUEST)

    assert response.metrics == []
    assert response.time_range == ApiTimeRange(start=0, end=60, step=10)


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_evaluates_as_the_token_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fetching the data queries livestatus, which filters by the logged-in user; evaluating as the
    # unauthenticated user this request otherwise is would not be filtered at all.
    evaluated_as: dict[str, object] = {}

    def _capture(_graphs: Sequence[Graph], _options: Mapping[str, object]) -> EvaluatedGraphs:
        evaluated_as["user_id"] = user.id
        return EvaluatedGraphs(
            graphs=[EvaluatedGraph(name="g", title="t", vertical_range=None, stacks=[], lines=[])],
            diagnostics=FetchDiagnostics(),
        )

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_built_graphs", _capture)
    impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [_built()])

    fetch_widget_graph_data_v1(api_context(dashboard_token()), _REQUEST)

    assert evaluated_as["user_id"] == UserId("cmkadmin")


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_takes_the_temperature_unit_from_the_dashboard_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The impersonation itself is covered by the token-issuer test.

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_built_graphs", _celsius_graph)
    impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [_built()])

    response = fetch_widget_graph_data_v1(
        api_context(dashboard_token(), default_temperature_unit="fahrenheit"), _REQUEST
    )

    [metric] = response.metrics
    assert metric.metadata.unit.symbol == "°F"
    assert metric.data_points == [68.0]


@pytest.mark.parametrize(
    "owner_unit, site_default, expected_symbol, expected_points",
    [
        pytest.param("fahrenheit", "celsius", "°F", [68.0], id="owner F, site C"),
        pytest.param("celsius", "fahrenheit", "°C", [20.0], id="owner C, site F"),
    ],
)
@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_takes_the_temperature_unit_from_the_owners_own_profile(
    monkeypatch: pytest.MonkeyPatch,
    owner_unit: Literal["celsius", "fahrenheit"],
    site_default: str,
    expected_symbol: str,
    expected_points: list[float],
) -> None:
    # The site default stands in for what a visitor would get: the owner's profile has to win
    # both ways round, or a shared dashboard would render in the reader's unit.
    owner_attrs: UserSpec = {"temperature_unit": owner_unit}
    with create_and_destroy_user(custom_attrs=owner_attrs, config=active_config) as (
        owner,
        _password,
    ):
        monkeypatch.setattr(fetch_graph_data_module, "evaluate_built_graphs", _celsius_graph)
        impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()}, issuer=owner)
        _discovering(monkeypatch, [_built()])

        response = fetch_widget_graph_data_v1(
            api_context(dashboard_token(issuer=owner), default_temperature_unit=site_default),
            _REQUEST,
        )

    [metric] = response.metrics
    assert metric.metadata.unit.symbol == expected_symbol
    assert metric.data_points == expected_points
