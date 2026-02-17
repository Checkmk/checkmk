#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Unit tests for CMK-29277: Graph widget error handling refactoring.

This test suite verifies that technical graph rendering errors are properly
caught and transformed into user-friendly messages using make_mk_missing_data_error().
"""

from unittest.mock import MagicMock, patch

import pytest

from livestatus import MKLivestatusNotFoundError

from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.exceptions import WidgetRenderError
from cmk.gui.dashboard.page_graph_widget import render_graph_widget_content
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing import MKGraphRecipeNotFoundError, MKGraphWidgetTooSmallError

_MOCK_DASHLET_CONFIG: TemplateGraphDashletConfig = {
    "type": "performance_graph",
    "graph_render_options": {},
    "timerange": "25h",
    "source": "",
}


@pytest.fixture(name="mock_ctx")
def fixture_mock_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.config.debug = False
    ctx.config.graph_timeranges = []
    ctx.config.default_temperature_unit = "celsius"
    return ctx


class TestGraphWidgetErrorHandling:
    """Test that graph widget errors are properly transformed into user-friendly messages."""

    @pytest.mark.parametrize(
        "exception_class,exception_message,expected_exception,expected_message",
        [
            pytest.param(
                MKGraphRecipeNotFoundError,
                "Failed to calculate a graph recipe.",
                MKMissingDataError,
                "No data was found with the current parameters of this widget.",
                id="recipe_not_found",
            ),
            pytest.param(
                MKGraphWidgetTooSmallError,
                "Either increase the widget height or disable the graph legend.",
                WidgetRenderError,
                "Either increase the widget height or disable the graph legend.",
                id="widget_too_small",
            ),
        ],
    )
    def test_render_graph_widget_content_error_handling(
        self,
        request_context: None,
        mock_ctx: MagicMock,
        exception_class: type[Exception],
        exception_message: str,
        expected_exception: type[Exception],
        expected_message: str,
    ) -> None:
        """Verify that graph rendering exceptions are caught and transformed into the correct
        user-facing error type with the appropriate message."""
        with patch(
            "cmk.gui.dashboard.page_graph_widget.host_service_graph_dashlet_cmk",
            side_effect=exception_class(exception_message),
        ):
            with patch("cmk.gui.dashboard.page_graph_widget.dashlet_registry"):
                with pytest.raises(expected_exception) as exc_info:
                    render_graph_widget_content(
                        ctx=mock_ctx,
                        dashlet_config=_MOCK_DASHLET_CONFIG,
                        widget_id="test_widget",
                    )
                assert expected_message in str(exc_info.value)

    @pytest.mark.parametrize(
        "exception_class,exception_message,expected_error_substring",
        [
            (
                MKLivestatusNotFoundError,
                "Host not found",
                "Service or host not found.",
            ),
        ],
    )
    def test_dashlet_init_catches_and_transforms_graph_exceptions(
        self,
        request_context: None,
        exception_class: type[Exception],
        exception_message: str,
        expected_error_substring: str,
    ) -> None:
        """Verify that graph exceptions during dashlet initialization are caught and transformed into MKMissingDataError."""

        with patch.object(TemplateGraphDashlet, "build_graph_specification") as mock_graph_spec:
            mock_spec_instance = MagicMock()
            mock_spec_instance.recipes.side_effect = exception_class(exception_message)
            mock_graph_spec.return_value = mock_spec_instance

            dashlet = TemplateGraphDashlet(dashlet=_MOCK_DASHLET_CONFIG)
            assert dashlet._init_exception is not None
            assert isinstance(dashlet._init_exception, MKMissingDataError)
            assert expected_error_substring in str(dashlet._init_exception)

    def test_resolve_site_missing_host_provides_specific_message(
        self,
        request_context: None,
    ) -> None:
        missing_host = "ghost-host"

        with patch("cmk.gui.dashboard.dashlet.dashlets.graph.sites.live") as live_mock:
            live_mock.return_value.query_value.side_effect = MKLivestatusNotFoundError(
                "Host not found"
            )

            with pytest.raises(MKMissingDataError) as exc_info:
                TemplateGraphDashlet._resolve_site(missing_host)

        error_message = str(exc_info.value)
        assert missing_host in error_message
        assert "could not be found on any active site" in error_message
