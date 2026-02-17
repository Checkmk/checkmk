#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Unit tests for Graph widget error handling.

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
from cmk.gui.dashboard.page_graph_widget import GraphWidgetPage, render_graph_widget_content
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.graphing import MKGraphRecipeNotFoundError, MKGraphWidgetTooSmallError


class TestGraphWidgetErrorHandling:
    """Test that graph widget errors are properly transformed into user-friendly messages."""

    @pytest.mark.parametrize(
        "exception_class,exception_message,expected_exception,expected_substring",
        [
            (
                MKGraphRecipeNotFoundError,
                "Failed to calculate a graph recipe.",
                MKMissingDataError,
                "No data was found with the current parameters of this widget",
            ),
            (
                MKGraphWidgetTooSmallError,
                "Either increase the widget height or disable the graph legend.",
                WidgetRenderError,
                "Either increase the widget height or disable the graph legend.",
            ),
        ],
    )
    def test_render_graph_widget_content_transforms_graph_exceptions(
        self,
        request_context: None,
        exception_class: type[Exception],
        exception_message: str,
        expected_exception: type[Exception],
        expected_substring: str,
    ) -> None:
        """Verify that graph-specific exceptions are caught and transformed into UI-facing errors."""
        mock_ctx = MagicMock()
        mock_ctx.config.debug = False
        mock_ctx.config.graph_timeranges = []
        mock_ctx.config.default_temperature_unit = "celsius"
        mock_dashlet_config: TemplateGraphDashletConfig = {
            "type": "performance_graph",
            "graph_render_options": {},
            "timerange": "25h",
            "source": "",
        }

        with patch(
            "cmk.gui.dashboard.page_graph_widget.host_service_graph_dashlet_cmk",
            side_effect=exception_class(exception_message),
        ):
            with patch("cmk.gui.dashboard.page_graph_widget.dashlet_registry"):
                with pytest.raises(expected_exception) as exc_info:
                    render_graph_widget_content(
                        ctx=mock_ctx,
                        dashlet_config=mock_dashlet_config,
                        widget_id="test_widget",
                    )
                error_message = str(exc_info.value)
                assert expected_substring in error_message

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

        mock_dashlet_spec: TemplateGraphDashletConfig = {
            "type": "performance_graph",
            "graph_render_options": {},
            "timerange": "25h",
            "source": "",
        }

        with patch.object(TemplateGraphDashlet, "build_graph_specification") as mock_graph_spec:
            mock_spec_instance = MagicMock()
            mock_spec_instance.recipes.side_effect = exception_class(exception_message)
            mock_graph_spec.return_value = mock_spec_instance

            dashlet = TemplateGraphDashlet(dashlet=mock_dashlet_spec)
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

            with pytest.raises(MKUserError) as exc_info:
                TemplateGraphDashlet._resolve_site(missing_host)

        error_message = str(exc_info.value)
        assert missing_host in error_message
        assert "could not be found on any active site" in error_message

    def test_graph_widget_page_renders_user_error_from_validation(
        self,
        request_context: None,
    ) -> None:
        page = GraphWidgetPage()
        mock_ctx = MagicMock()
        user_message = "Host ghost-host is missing"

        with (
            patch(
                "cmk.gui.dashboard.page_graph_widget.get_validated_internal_graph_request",
                side_effect=MKUserError(None, user_message),
            ),
            patch(
                "cmk.gui.dashboard.page_graph_widget.html.render_message",
                return_value="rendered",
            ) as render_message,
            patch(
                "cmk.gui.dashboard.page_graph_widget.html.write_html",
            ) as write_html,
        ):
            page.page(mock_ctx)

        render_message.assert_called_once_with(user_message)
        write_html.assert_called_once_with("rendered")
