#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The consolidation function selector on the service detail page's graphs.

Test that each consolidation function selection refetches the panel's series with the picked
consolidation function and that the picked function is preserved on the redrawn graph.
"""

import json
import logging
from collections.abc import Callable
from typing import Final

from playwright.sync_api import expect, Request

from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs

logger = logging.getLogger(__name__)

_GRAPH_DATA_URL: Final = "/domain-types/graph/actions/fetch_data/invoke"

# Above 48 hours, so the RRD data is consolidated and the function actually chooses between
# distinct aggregates rather than the raw samples it would serve for a shorter window.
_WIDE_WINDOW_PRESET: Final = "Last 8 d"

_DEFAULT_LABEL: Final = "Max"
_SELECTIONS: Final = [("Min", "min"), ("Average", "avg")]


def _request_carries_consolidation_selection(wire_value: str) -> Callable[[Request], bool]:
    """Match a graph-data POST whose body asks for the `wire_value` consolidation function."""

    def matches(request: Request) -> bool:
        if _GRAPH_DATA_URL not in request.url or request.method != "POST":
            return False
        body = request.post_data
        return body is not None and json.loads(body).get("consolidation_function") == wire_value

    return matches


def test_selecting_a_consolidation_function_refetches_and_redraws_the_graph(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """Each consolidation selection reaches the backend and is preserved on the graph."""
    service_graphs.time_picker.select_preset(_WIDE_WINDOW_PRESET)
    service_graphs.wait_until_settled()

    panel = service_graphs.panel(0)
    expect(
        panel.consolidation_control,
        "The graph did not start on its default consolidation function",
    ).to_contain_text(_DEFAULT_LABEL)

    for option_label, wire_value in _SELECTIONS:
        with panel.page.expect_request(_request_carries_consolidation_selection(wire_value)):
            panel.select_consolidation(option_label)
        service_graphs.wait_until_settled()
        expect(
            panel.consolidation_control,
            f"The control did not show {option_label!r} after it was picked",
        ).to_contain_text(option_label)

    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"
