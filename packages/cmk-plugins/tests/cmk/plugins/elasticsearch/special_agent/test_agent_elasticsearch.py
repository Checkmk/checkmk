#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from cmk.plugins.elasticsearch.special_agent.agent_elasticsearch import (
    agent_elasticsearch_main,
    parse_arguments,
)

_HEALTH_RESPONSE = {
    "cluster_name": "test-cluster",
    "status": "green",
    "number_of_nodes": 1,
}

_NODE_STATS_RESPONSE = {
    "nodes": {
        "node-1": {
            "name": "node-1",
            "process": {
                "open_file_descriptors": 100,
                "max_file_descriptors": 4096,
                "cpu": {"percent": 5, "total_in_millis": 12345},
                "mem": {"total_virtual_in_bytes": 2147483648},
            },
        }
    }
}


def _make_response(
    status_code: int, json_payload: object | None = None, text: str = ""
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_payload
    return response


@pytest.fixture
def stub_requests(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, MagicMock]]:
    """Map URL substrings to canned responses; return the dict so tests can override."""
    responses: dict[str, MagicMock] = {
        "/_cluster/health": _make_response(200, _HEALTH_RESPONSE),
        "/_nodes/stats/process": _make_response(200, _NODE_STATS_RESPONSE),
    }

    def fake_get(url: str, **_kwargs: object) -> MagicMock:
        for fragment, response in responses.items():
            if fragment in url:
                return response
        raise AssertionError(f"unexpected URL requested: {url}")

    monkeypatch.setattr(
        "cmk.plugins.elasticsearch.special_agent.agent_elasticsearch.requests.get",
        fake_get,
    )
    yield responses


def test_happy_path_emits_both_sections(
    stub_requests: dict[str, MagicMock], capsys: pytest.CaptureFixture[str]
) -> None:
    rc = agent_elasticsearch_main(
        parse_arguments(["--cluster-health", "--nodes", "-P", "https", "myhost"])
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "<<<elasticsearch_cluster_health" in captured.out
    assert "<<<elasticsearch_nodes" in captured.out
    assert captured.err == ""


def test_http_400_on_nodes_does_not_drop_cluster_health(
    stub_requests: dict[str, MagicMock], capsys: pytest.CaptureFixture[str]
) -> None:
    """Regression: AWS OpenSearch returns HTTP 400 on /_nodes/.../stats due to
    integer overflow in unused stats categories. The agent must skip the failing
    section, log to stderr, and still emit cluster_health."""
    stub_requests["/_nodes/stats/process"] = _make_response(
        400,
        text='{"error":{"type":"illegal_argument_exception"}}',
    )

    rc = agent_elasticsearch_main(
        parse_arguments(["--cluster-health", "--nodes", "-P", "https", "myhost"])
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "<<<elasticsearch_cluster_health" in captured.out
    assert "<<<elasticsearch_nodes" not in captured.out
    assert "HTTP 400" in captured.err


def test_decode_error_in_earlier_section_does_not_drop_later_section(
    stub_requests: dict[str, MagicMock], capsys: pytest.CaptureFixture[str]
) -> None:
    """A 200 response with malformed JSON (or a ValidationError) in an earlier
    section must be isolated: log to stderr, skip that section, and still emit
    the later section."""
    broken = _make_response(200)
    broken.json.side_effect = ValueError("Expecting value")
    stub_requests["/_cluster/health"] = broken

    rc = agent_elasticsearch_main(
        parse_arguments(["--cluster-health", "--nodes", "-P", "https", "myhost"])
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "<<<elasticsearch_cluster_health" not in captured.out
    assert "<<<elasticsearch_nodes" in captured.out
    assert "Error decoding" in captured.err


def test_validation_error_in_nodes_is_isolated(
    stub_requests: dict[str, MagicMock], capsys: pytest.CaptureFixture[str]
) -> None:
    """A ValidationError inside handle_nodes (the original AWS OpenSearch trigger)
    must be caught and logged without aborting, leaving cluster_health intact."""
    stub_requests["/_nodes/stats/process"] = _make_response(200, {"nodes": {"node-1": {}}})

    rc = agent_elasticsearch_main(
        parse_arguments(["--cluster-health", "--nodes", "-P", "https", "myhost"])
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "<<<elasticsearch_cluster_health" in captured.out
    assert "Error decoding" in captured.err


def test_section_order_is_deterministic(
    stub_requests: dict[str, MagicMock], capsys: pytest.CaptureFixture[str]
) -> None:
    """cluster_health must appear before nodes regardless of which one fails,
    so a later failure cannot retroactively suppress an earlier section's
    output (the original `set()` made this non-deterministic)."""
    agent_elasticsearch_main(
        parse_arguments(["--cluster-health", "--nodes", "-P", "https", "myhost"])
    )
    out = capsys.readouterr().out
    assert out.index("<<<elasticsearch_cluster_health") < out.index("<<<elasticsearch_nodes")
