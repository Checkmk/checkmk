#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the token-authenticated graph widget data fetch."""

import datetime as dt
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import cast
from unittest.mock import MagicMock

import pytest

from cmk.ccc.user import UserId
from cmk.graphing_engine import EvaluatedGraph, Graph
from cmk.gui.dashboard.api import fetch_widget_graph_data as endpoint_module
from cmk.gui.dashboard.api.fetch_widget_graph_data import (
    fetch_widget_graph_data_v1,
    WidgetGraphFetchRequest,
)
from cmk.gui.dashboard.dashlet.dashlets.graph import TemplateGraphDashlet
from cmk.gui.dashboard.token_util import InvalidWidgetError
from cmk.gui.dashboard.type_defs import DashboardConfig, DashletConfig
from cmk.gui.graphing._engine_discovery import BuiltGraph, DiscoveredGraphs
from cmk.gui.graphing._engine_dispatch import EvaluatedGraphs
from cmk.gui.graphing._engine_source import FetchDiagnostics
from cmk.gui.graphing.openapi import fetch_graph_data as fetch_graph_data_module
from cmk.gui.graphing.openapi.models import ApiTimeRange
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentDownloadToken, AuthToken, DashboardToken, TokenId
from cmk.gui.utils.roles import UserPermissions

_WIDGET_ID = "test_dashboard-0"

_REQUEST = WidgetGraphFetchRequest(
    widget_id=_WIDGET_ID,
    requested_time_range=ApiTimeRange(start=0, end=60, step=10),
    consolidation_function="avg",
)


def _built() -> BuiltGraph:
    return BuiltGraph(graph=Graph(name="g", title="t", kind="template"), specification=None)


def _dashboard_token(*, disabled: bool = False) -> AuthToken:
    return AuthToken(
        issuer=UserId("cmkadmin"),
        issued_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        valid_until=None,
        token_id=TokenId("the-token"),
        details=DashboardToken(
            owner=UserId("cmkadmin"),
            dashboard_name="test_dashboard",
            disabled=disabled,
            synced_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        ),
    )


def _agent_download_token() -> AuthToken:
    return AuthToken(
        issuer=UserId("cmkadmin"),
        issued_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        valid_until=None,
        token_id=TokenId("the-token"),
        details=AgentDownloadToken(),
    )


def _api_context(token: AuthToken | None) -> ApiContext:
    """The two configuration values the fetch needs; the rest is irrelevant here."""
    context = MagicMock(spec=ApiContext)
    context.token = token
    context.config.debug = False
    context.config.user_permissions.return_value = UserPermissions({}, {}, {}, [])
    return context


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


def _impersonating_but_unpermitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The issuer may no longer see the dashboard the token was issued for.

    `load_dashboard` signals that by raising with `disable_token`, and it runs before the widget
    lookup - so the handler has to catch it outside the impersonation, not around the lookup.
    """

    @contextmanager
    def _impersonate(
        issuer: UserId, _details: object, permissions: UserPermissions
    ) -> Iterator[MagicMock]:
        from cmk.gui.session_context import UserContext

        with UserContext(issuer, permissions):
            loaded = MagicMock()
            loaded.load_dashboard.side_effect = InvalidWidgetError(disable_token=True)
            yield loaded

    monkeypatch.setattr(endpoint_module, "impersonate_dashboard_token_issuer", _impersonate)


def _impersonating(monkeypatch: pytest.MonkeyPatch, widgets: dict[str, DashletConfig]) -> None:
    """Stand in for the token issuer impersonation, which the token pages cover.

    The stub still enters a `UserContext`, so the tests can tell what the fetch runs as.
    """
    board = cast(
        DashboardConfig,
        {
            "name": "test_dashboard",
            "owner": "cmkadmin",
            "context": {},
            "widgets": widgets,
        },
    )

    @contextmanager
    def _impersonate(
        issuer: UserId, _details: object, permissions: UserPermissions
    ) -> Iterator[MagicMock]:
        from cmk.gui.session_context import UserContext

        with UserContext(issuer, permissions):
            loaded = MagicMock()
            loaded.load_dashboard.return_value = board
            yield loaded

    monkeypatch.setattr(endpoint_module, "impersonate_dashboard_token_issuer", _impersonate)


def _discovering(monkeypatch: pytest.MonkeyPatch, graphs: Sequence[BuiltGraph]) -> None:
    monkeypatch.setattr(
        TemplateGraphDashlet,
        "discover_graphs",
        lambda _self, **_kwargs: DiscoveredGraphs(graphs=graphs, no_data_message=None),
    )


def test_fetch_without_a_token_is_401() -> None:
    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(None), _REQUEST)
    assert exc_info.value.code == 401


def test_fetch_with_a_token_of_another_kind_is_401() -> None:
    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_agent_download_token()), _REQUEST)
    assert exc_info.value.code == 401


def test_fetch_with_a_disabled_dashboard_token_is_401() -> None:
    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token(disabled=True)), _REQUEST)
    assert exc_info.value.code == 401


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_a_widget_outside_the_dashboard_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    _impersonating(monkeypatch, {"test_dashboard-1": _graph_widget()})

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_a_non_graph_widget_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    _impersonating(monkeypatch, {_WIDGET_ID: _graph_widget("static_text")})

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_a_widget_without_a_discovered_graph_is_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [])

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_evaluates_the_widgets_discovered_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    # An empty graph has no metrics, so this runs end to end without a livestatus fixture.
    _impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [_built()])

    response = fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert response.metrics == []
    assert response.time_range == ApiTimeRange(start=0, end=60, step=10)


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_takes_the_combination_mode_from_the_widget_not_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Mapping[str, object]] = {}

    def _capture(_graphs: Sequence[Graph], options: Mapping[str, object]) -> EvaluatedGraphs:
        captured["options"] = options
        return EvaluatedGraphs(
            graphs=[EvaluatedGraph(name="g", title="t", vertical_range=None, stacks=[], lines=[])],
            diagnostics=FetchDiagnostics(),
        )

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_built_graphs", _capture)
    _impersonating(
        monkeypatch,
        {_WIDGET_ID: _graph_widget("combined_graph", presentation="stacked", graph_template="cpu")},
    )
    monkeypatch.setattr(
        endpoint_module,
        "discover_widget_graphs",
        lambda *_args, **_kwargs: DiscoveredGraphs(graphs=[_built()], no_data_message=None),
    )

    # The request carries no combination mode; only the widget's configuration can decide it.
    fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert captured["options"]["combination_mode"] == "stacked"


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
    _impersonating(monkeypatch, {_WIDGET_ID: _graph_widget()})
    _discovering(monkeypatch, [_built()])

    fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert evaluated_as["user_id"] == UserId("cmkadmin")


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_a_dashboard_the_issuer_may_no_longer_see_is_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Raised by load_dashboard, i.e. before the widget lookup: handling it only around the lookup
    # would let it escape as an unhandled error.
    _impersonating_but_unpermitted(monkeypatch)
    monkeypatch.setattr(endpoint_module, "disable_dashboard_token_by_id", lambda _token_id: None)

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_retires_a_token_that_no_longer_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    # A token whose dashboard the issuer lost access to must stop working, as it does on the pages.
    disabled: list[TokenId] = []
    _impersonating_but_unpermitted(monkeypatch)
    monkeypatch.setattr(endpoint_module, "disable_dashboard_token_by_id", disabled.append)

    with pytest.raises(ProblemException):
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert disabled == [TokenId("the-token")]


@pytest.mark.usefixtures("load_config", "request_context")
def test_fetch_of_an_unknown_widget_leaves_the_token_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A bad widget ID says nothing about the token, so it keeps working.
    disabled: list[TokenId] = []
    _impersonating(monkeypatch, {"test_dashboard-1": _graph_widget()})
    monkeypatch.setattr(endpoint_module, "disable_dashboard_token_by_id", disabled.append)

    with pytest.raises(ProblemException) as exc_info:
        fetch_widget_graph_data_v1(_api_context(_dashboard_token()), _REQUEST)

    assert exc_info.value.code == 404
    assert disabled == []
