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
from cmk.gui.dashboard.page_graph_widget import render_graph_widget_content
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing import (
    MKGraphDashletTooSmallError,
    MKGraphRecipeCalculationError,
    MKGraphRecipeNotFoundError,
)


class TestGraphWidgetErrorHandling:
    """Test that graph widget errors are properly transformed into user-friendly messages."""

    @pytest.mark.parametrize(
        "exception_class,exception_message",
        [
            (
                MKGraphRecipeCalculationError,
                "Cannot calculate graph recipes",
            ),
            (
                MKGraphRecipeNotFoundError,
                "Failed to calculate a graph recipe.",
            ),
            (
                MKGraphDashletTooSmallError,
                "Either increase the dashlet height or disable the graph legend.",
            ),
        ],
    )
    def test_render_graph_widget_content_transforms_graph_exceptions(
        self,
        request_context: None,
        exception_class: type[Exception],
        exception_message: str,
    ) -> None:
        """Verify that graph-specific exceptions are caught and transformed into MKMissingDataError."""
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
                with pytest.raises(MKMissingDataError) as exc_info:
                    render_graph_widget_content(
                        ctx=mock_ctx,
                        dashlet_config=mock_dashlet_config,
                        widget_id="test_widget",
                    )
                error_message = str(exc_info.value)
                assert (
                    "No data was found with the current parameters of this widget" in error_message
                )

    @pytest.mark.parametrize(
        "exception_class,exception_message,expected_error_substring",
        [
            (
                MKGraphRecipeNotFoundError,
                "Failed to calculate a graph recipe.",
                "No data was found with the current parameters of this widget",
            ),
            (
                MKLivestatusNotFoundError,
                "Host not found",
                "Service or host not found.",
            ),
            (
                MKGraphDashletTooSmallError,
                "Dashlet too small",
                "No data was found with the current parameters of this widget",
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

    @pytest.mark.parametrize(
        "exception_class,exception_message,expected_user_message",
        [
            (
                MKGraphRecipeCalculationError,
                "INTERNAL ERROR: failed to load metric backend",
                "No data was found with the current parameters of this widget.",
            ),
            (
                MKGraphRecipeNotFoundError,
                "Failed to calculate a graph recipe.",
                "No data was found with the current parameters of this widget.",
            ),
        ],
    )
    def test_render_graph_widget_error_handling(
        self,
        request_context: None,
        exception_class: type[Exception],
        exception_message: str,
        expected_user_message: str,
    ) -> None:
        """Verify that render_graph_widget_content transforms exceptions into user-friendly messages, hiding technical details."""

        mock_ctx = MagicMock()
        mock_ctx.config.debug = False
        mock_ctx.config.graph_timeranges = []
        mock_ctx.config.default_temperature_unit = "celsius"
        mock_ctx.request = MagicMock()

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
                with pytest.raises(MKMissingDataError) as exc_info:
                    render_graph_widget_content(
                        ctx=mock_ctx,
                        dashlet_config=mock_dashlet_config,
                        widget_id="test_widget",
                    )

                error_message = str(exc_info.value)
                assert error_message == expected_user_message
