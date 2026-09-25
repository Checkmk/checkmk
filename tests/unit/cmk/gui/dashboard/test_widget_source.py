#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

import pytest

from cmk.gui.dashboard.api import (
    ExplicitWidgetContent,
    resolve_widget,
    SavedWidgetContent,
    WidgetTimeRange,
)
from cmk.gui.dashboard.api.model.widget_content.stats import HostStatsContent
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.logged_in import user
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client import MKLivestatusException
from tests.unit.cmk.gui.helpers.dashboard_widget_resolution_test_helper import (
    api_context,
    dashboard_token,
    dashboard_widget,
    impersonating,
    impersonating_but_unpermitted,
    ISSUER,
    recording_token_retirement,
    TOKEN_ID,
    WIDGET_ID,
)

_STATS_TYPES = frozenset({"hoststats"})
_SAVED = SavedWidgetContent(type="saved", widget_id=WIDGET_ID)


def _no_built_in_link(_content: HostStatsContent) -> None:
    return None


def _explicit(
    context: dict[str, dict[str, str]] | None = None,
) -> ExplicitWidgetContent[HostStatsContent]:
    return ExplicitWidgetContent(
        type="explicit", content=HostStatsContent(type="host_stats"), context=context or {}
    )


def _problem(
    source: ExplicitWidgetContent[HostStatsContent] | SavedWidgetContent, *, token: bool
) -> ProblemException:
    with (
        pytest.raises(ProblemException) as exc_info,
        resolve_widget(
            api_context(dashboard_token() if token else None),
            source,
            _STATS_TYPES,
            _no_built_in_link,
        ),
    ):
        pass
    return exc_info.value


def _raised_from_the_handler(exception: Exception) -> ProblemException:
    with (
        pytest.raises(ProblemException) as exc_info,
        resolve_widget(api_context(None), _explicit(), _STATS_TYPES, _no_built_in_link),
    ):
        raise exception
    return exc_info.value


@pytest.mark.usefixtures("load_config", "request_context")
def test_an_explicit_source_resolves_the_sent_content_and_context() -> None:
    context = {"host": {"host": "my-host"}}

    with resolve_widget(
        api_context(None), _explicit(context), _STATS_TYPES, _no_built_in_link
    ) as widget:
        assert widget.config == {"type": "hoststats"}
        assert widget.context == context


@pytest.mark.usefixtures("load_config", "request_context")
def test_the_infos_come_from_the_dashlet_class(monkeypatch: pytest.MonkeyPatch) -> None:
    impersonating(monkeypatch, {WIDGET_ID: dashboard_widget()})

    with resolve_widget(
        api_context(dashboard_token()), _SAVED, _STATS_TYPES, _no_built_in_link
    ) as widget:
        assert widget.infos == ["host"]


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_saved_source_resolves_the_stored_widget(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = dashboard_widget(context={"host": {"host": "my-host"}})
    impersonating(monkeypatch, {WIDGET_ID: stored})

    with resolve_widget(
        api_context(dashboard_token()), _SAVED, _STATS_TYPES, _no_built_in_link
    ) as widget:
        assert widget.config == stored


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_saved_source_merges_the_dashboard_context_under_the_widget_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impersonating(
        monkeypatch,
        {WIDGET_ID: dashboard_widget(context={"host": {"host": "widget-host"}})},
        dashboard_context={"host": {"host": "dashboard-host"}, "site": {"site": "heute"}},
    )

    with resolve_widget(
        api_context(dashboard_token()), _SAVED, _STATS_TYPES, _no_built_in_link
    ) as widget:
        assert widget.context == {"host": {"host": "widget-host"}, "site": {"site": "heute"}}


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_saved_source_queries_as_the_token_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    impersonating(monkeypatch, {WIDGET_ID: dashboard_widget()})

    with resolve_widget(api_context(dashboard_token()), _SAVED, _STATS_TYPES, _no_built_in_link):
        assert user.id == ISSUER


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_token_may_not_send_a_configuration() -> None:
    assert _problem(_explicit(), token=True).code == 403


def test_a_saved_source_without_a_token_is_401() -> None:
    assert _problem(_SAVED, token=False).code == 401


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_widget_type_the_endpoint_rejects_is_400(monkeypatch: pytest.MonkeyPatch) -> None:
    impersonating(monkeypatch, {WIDGET_ID: dashboard_widget("servicestats")})

    assert _problem(_SAVED, token=True).code == 400


def test_a_start_not_before_its_end_is_rejected() -> None:
    moment = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    with pytest.raises(ValueError):
        WidgetTimeRange(start=moment, end=moment)


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_missing_data_error_is_404() -> None:
    problem = _raised_from_the_handler(MKMissingDataError("Nothing found"))

    assert (problem.code, problem.description) == (404, "No data available")


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_user_error_is_404() -> None:
    problem = _raised_from_the_handler(MKUserError(None, "The context lacks a host"))

    assert (problem.code, problem.description) == (404, "No data available")


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_livestatus_error_is_503() -> None:
    assert _raised_from_the_handler(MKLivestatusException("Site down")).code == 503


@pytest.mark.usefixtures("load_config", "request_context")
def test_an_unmapped_exception_is_not_translated() -> None:
    with (
        pytest.raises(KeyError),
        resolve_widget(api_context(None), _explicit(), _STATS_TYPES, _no_built_in_link),
    ):
        raise KeyError("unexpected")


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_saved_source_for_a_missing_widget_is_404_and_keeps_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impersonating(monkeypatch, {"test_dashboard-1": dashboard_widget()})
    disabled = recording_token_retirement(monkeypatch)

    problem = _problem(_SAVED, token=True)

    assert (problem.code, problem.description) == (404, "Widget not found")
    assert disabled == []


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_dashboard_that_no_longer_resolves_retires_its_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impersonating_but_unpermitted(monkeypatch)
    disabled = recording_token_retirement(monkeypatch)

    assert _problem(_SAVED, token=True).code == 404
    assert disabled == [TOKEN_ID]


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_widget_of_an_unknown_type_retires_its_token(monkeypatch: pytest.MonkeyPatch) -> None:
    impersonating(monkeypatch, {WIDGET_ID: dashboard_widget("removed_by_a_downgrade")})
    disabled = recording_token_retirement(monkeypatch)

    problem = _problem(_SAVED, token=True)

    assert (problem.code, problem.description) == (404, "Widget not found")
    assert disabled == [TOKEN_ID]
