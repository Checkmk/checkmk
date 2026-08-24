#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Unit tests for Graph widget error handling.

This test suite verifies that technical graph rendering errors are properly
caught and transformed into user-friendly messages using make_mk_missing_data_error().
"""

import re
from unittest.mock import MagicMock, patch

import pytest

from livestatus import MKLivestatusNotFoundError

from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.exceptions import WidgetRenderError
from cmk.gui.exceptions import MKMissingDataError


class TestGraphWidgetErrorHandling:
    """Test that graph widget errors are properly transformed into user-friendly messages."""

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
    def test_recipes_transforms_graph_exceptions(
        self,
        request_context: None,
        exception_class: type[Exception],
        exception_message: str,
        expected_error_substring: str,
    ) -> None:
        """Verify that graph exceptions are transformed into MKMissingDataError."""

        mock_dashlet_spec: TemplateGraphDashletConfig = {
            "type": "performance_graph",
            "graph_render_options": {},
            "timerange": "25h",
            "graph_id": "",
        }

        with patch.object(TemplateGraphDashlet, "build_graph_specification") as mock_graph_spec:
            mock_spec_instance = MagicMock()
            mock_spec_instance.recipes.side_effect = exception_class(exception_message)
            mock_graph_spec.return_value = mock_spec_instance

            dashlet = TemplateGraphDashlet(dashlet=mock_dashlet_spec)
            with pytest.raises(MKMissingDataError, match=re.escape(expected_error_substring)):
                dashlet.recipes()

    def test_instantiation_does_not_resolve_the_graph(self, request_context: None) -> None:
        """Serving a dashboard instantiates every widget; resolving queries the core, so the
        recipes must only be computed once something asks for them."""
        mock_dashlet_spec: TemplateGraphDashletConfig = {
            "type": "performance_graph",
            "graph_render_options": {},
            "timerange": "25h",
            "graph_id": "",
        }

        with patch.object(TemplateGraphDashlet, "build_graph_specification") as mock_graph_spec:
            dashlet = TemplateGraphDashlet(dashlet=mock_dashlet_spec)
            assert mock_graph_spec.call_count == 0

            # Reporting the infos the widget's filters use must stay free of graph resolution.
            assert dashlet.infos() == ["host", "service"]
            assert mock_graph_spec.call_count == 0

            dashlet.recipes()
            assert mock_graph_spec.call_count == 1

            # Resolution is memoized: a second consumer must not query the core again.
            dashlet.default_display_title()
            assert mock_graph_spec.call_count == 1

    def test_resolve_site_missing_host_provides_specific_message(
        self,
        request_context: None,
    ) -> None:
        missing_host = "ghost-host"

        with patch("cmk.gui.dashboard.dashlet.dashlets.graph.sites.live") as live_mock:
            live_mock.return_value.query_value.side_effect = MKLivestatusNotFoundError(
                "Host not found"
            )

            with pytest.raises(WidgetRenderError) as exc_info:
                TemplateGraphDashlet._resolve_site(missing_host)

        error_message = str(exc_info.value)
        assert missing_host in error_message
        assert "could not be found on any active site" in error_message
