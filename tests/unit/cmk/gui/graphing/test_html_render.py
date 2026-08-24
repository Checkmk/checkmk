#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import html as html_escaping
import json
import re

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.graphing._html_render import host_service_graph_popup_cmk
from cmk.gui.utils.output_funnel import output_funnel
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.servicename import ServiceName

# The engine resolves the metric names during the render with a single services query.
_POPUP_SERVICE_ROW = {
    "host_name": "h",
    "description": "svc",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check_mk-foo",
}
_POPUP_ENGINE_QUERY = (
    "GET services\nColumns: host_name description perf_data metrics check_command\n"
    "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
)


def _render_popup(mock_livestatus: MockLiveStatusConnection) -> str:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("services", [_POPUP_SERVICE_ROW])
    mock_livestatus.expect_query(_POPUP_ENGINE_QUERY)
    with mock_livestatus(), output_funnel.plugged():
        host_service_graph_popup_cmk(
            None,
            HostName("h"),
            ServiceName("svc"),
            debug=False,
        )
        return output_funnel.drain()


def _component_payload(output: str) -> dict[str, object]:
    """The props the ``cmk-graph-group`` element was mounted with."""
    match = re.search(r'<cmk-graph-group data="([^"]*)"', output)
    assert match, f"No cmk-graph-group element in the rendered popup: {output}"
    payload = json.loads(html_escaping.unescape(match.group(1)))
    assert isinstance(payload, dict)
    return payload


def test_host_service_graph_popup_renders_the_new_engine_component(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    output = _render_popup(mock_livestatus)

    # The hover preview renders the service graph through the engine's Vue component ...
    assert "cmk-graph-group" in output
    # ... on the hover graph surface (the wrapper carries the background the component omits) ...
    assert 'class="cmk_graph_hover"' in output
    # ... at the compact popup size (30x10 ex * HTML_SIZE_PER_EX = 330x110 px), not the
    # group's in-view default. Read off the parsed props: a substring check would pass on
    # any digit run containing these numbers, wherever it came from.
    payload = _component_payload(output)
    assert payload["figure_width"] == 330
    assert payload["figure_height"] == 110
