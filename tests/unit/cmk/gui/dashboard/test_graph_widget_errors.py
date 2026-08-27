#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Unit tests for Graph widget error handling.

This test suite verifies that technical graph rendering errors are properly
caught and transformed into user-friendly messages.
"""

from unittest.mock import patch

import pytest

from livestatus import MKLivestatusNotFoundError

from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.exceptions import WidgetRenderError


class TestGraphWidgetErrorHandling:
    """Test that graph widget errors are properly transformed into user-friendly messages."""

    def test_instantiation_does_not_resolve_the_graph(self, request_context: None) -> None:
        """Serving a dashboard instantiates every widget; resolving queries the core, so the
        specification must only be built once something asks for it."""
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

            dashlet.graph_specification()
            assert mock_graph_spec.call_count == 1

            # Resolution is memoized: a second consumer must not query the core again.
            dashlet.graph_specification()
            assert mock_graph_spec.call_count == 1

    def test_a_widget_whose_graph_cannot_be_resolved_keeps_its_own_title(
        self, request_context: None
    ) -> None:
        mock_dashlet_spec: TemplateGraphDashletConfig = {
            "type": "performance_graph",
            "graph_render_options": {},
            "timerange": "25h",
            "graph_id": "",
        }

        with patch.object(
            TemplateGraphDashlet,
            "build_graph_specification",
            side_effect=MKLivestatusNotFoundError("Host not found"),
        ):
            dashlet = TemplateGraphDashlet(dashlet=mock_dashlet_spec)

            assert dashlet.default_display_title() == TemplateGraphDashlet.title()

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
