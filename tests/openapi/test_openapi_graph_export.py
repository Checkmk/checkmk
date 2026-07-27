#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from urllib.parse import parse_qs, urlparse

from tests.testlib.rest_api_client import ClientRegistry

_TEMPLATE_SPEC = {
    "graph_type": "template",
    "site": "NO_SITE",
    "host_name": "my-host",
    "service_description": "CPU load",
    "graph_id": "cpu_load",
}


def _export_request_of(download_url: str) -> dict[str, object]:
    [raw] = parse_qs(urlparse(download_url).query)["request"]
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    return parsed


def test_export_prepares_the_download_of_the_displayed_graph(clients: ClientRegistry) -> None:
    # The browser posts the graph in the API's own vocabulary and follows the prepared URL; the
    # legacy page name, its request envelope and its spelling of the average are the server's.
    download_url = clients.Graph.export(
        specification=_TEMPLATE_SPEC,
        target="graph_image",
        consolidation_function="avg",
        time_start=1781524800,
        time_end=1781528400,
    ).json["download_url"]

    assert download_url.startswith("graph_image.py?")
    assert _export_request_of(download_url) == {
        # The whole specification as the page parses it back, defaults included.
        "specification": {**_TEMPLATE_SPEC, "id": None, "destination": None},
        # "avg" on the wire, spelled out for the legacy page.
        "consolidation_function": "average",
        "time_start": 1781524800,
        "time_end": 1781528400,
    }


def test_export_without_a_range_leaves_the_defaults_to_the_export_page(
    clients: ClientRegistry,
) -> None:
    # Omitted bounds stay omitted: the page defaults them to the last 25 hours itself.
    request = _export_request_of(
        clients.Graph.export(specification=_TEMPLATE_SPEC, target="graph_export").json[
            "download_url"
        ]
    )

    assert request["time_start"] is None
    assert request["time_end"] is None
    assert request["consolidation_function"] == "max"


def test_export_rejects_an_unparseable_specification(clients: ClientRegistry) -> None:
    response = clients.Graph.export(
        specification={"graph_type": "no_such_graph_type"},
        target="graph_export",
        expect_ok=False,
    )

    response.assert_status_code(400)
    assert response.json["title"] == "Invalid graph specification"
