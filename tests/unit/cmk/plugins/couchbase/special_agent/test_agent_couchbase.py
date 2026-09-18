#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys
from collections.abc import Mapping, Sequence

import pytest
import requests
import responses

from cmk.password_store.v1_unstable import resolve_secret_option
from cmk.plugins.couchbase.special_agent import agent_couchbase

HOST = "couchbase.example.com"
PORT = 8091
BASE = f"http://{HOST}:{PORT}/pools/default"

POOL_RESPONSE = {
    "nodes": [
        {
            "hostname": "node-1.example.com:8091",
            "uptime": "3600",
            "status": "healthy",
            "clusterMembership": "active",
            "version": "7.1.0",
            "services": ["kv", "n1ql"],
            "ports": {"direct": 11210},
            "systemStats": {"cpu_utilization_rate": 12.5, "mem_total": 1024, "ignored": 1},
            "interestingStats": {"ops": 42, "curr_items": 7, "get_hits": 3},
        },
        {
            "hostname": "node-2.example.com:8091",
            "uptime": "60",
            "status": "warmup",
        },
    ]
}

BUCKET_RESPONSE = {
    "op": {
        "samples": {
            "ops": [1.0, 2.0, 3.0],
            "mem_total": [100.0],
            "ep_cache_miss_rate": [],
            "unknown_key": [5.0],
        }
    }
}


def _sections(output: str) -> Mapping[str, Sequence[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] = []
    for line in output.splitlines():
        if line.startswith("<<<") and line.endswith(">>>"):
            current = sections.setdefault(line[3:-3].split(":")[0], [])
        else:
            current.append(line)
    return sections


def _json_lines(lines: Sequence[str]) -> Sequence[Mapping[str, object]]:
    return [json.loads(line) for line in lines]


def _run(argv: Sequence[str]) -> int:
    return agent_couchbase.couchbase_main(agent_couchbase.parse_arguments(argv))


def test_parse_arguments_defaults() -> None:
    args = agent_couchbase.parse_arguments([HOST])

    assert args.hostname == HOST
    assert args.port == 8091
    assert args.timeout == 10
    assert args.buckets == []
    assert args.username is None
    assert args.debug is False
    assert args.verbose == 0


def test_parse_arguments_collects_repeated_buckets() -> None:
    args = agent_couchbase.parse_arguments(["-b", "first", "--buckets", "second", HOST])

    assert args.buckets == ["first", "second"]


def test_parse_arguments_resolves_explicit_password() -> None:
    args = agent_couchbase.parse_arguments(
        ["-u", "admin", "--password", "top-secret", "-P", "9000", "-t", "3", "-vv", "-d", HOST]
    )

    assert args.username == "admin"
    assert resolve_secret_option(args, agent_couchbase.PASSWORD_OPTION).reveal() == "top-secret"
    assert args.port == 9000
    assert args.timeout == 3
    assert args.verbose == 2
    assert args.debug is True


def test_parse_arguments_requires_hostname() -> None:
    with pytest.raises(SystemExit):
        agent_couchbase.parse_arguments([])


@pytest.mark.parametrize(
    "verbosity",
    [
        pytest.param(0, id="warning"),
        pytest.param(1, id="info"),
        pytest.param(2, id="debug"),
    ],
)
def test_set_up_logging_accepts_all_verbosity_levels(verbosity: int) -> None:
    agent_couchbase.set_up_logging(verbosity)


@responses.activate
def test_node_string_sections_list_every_node(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json=POOL_RESPONSE)

    exit_code = _run([HOST])

    sections = _sections(capsys.readouterr().out)
    assert exit_code == 0
    assert sections["couchbase_nodes_uptime"] == [
        "3600 node-1.example.com",
        "60 node-2.example.com",
    ]
    assert sections["couchbase_nodes_operations"] == [
        "42 node-1.example.com",
        "None node-2.example.com",
    ]


@responses.activate
def test_node_json_sections_only_contain_known_keys(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json=POOL_RESPONSE)

    _run([HOST])

    sections = _sections(capsys.readouterr().out)
    assert _json_lines(sections["couchbase_nodes_info"]) == [
        {
            "name": "node-1.example.com",
            "clusterMembership": "active",
            "status": "healthy",
            "version": "7.1.0",
        },
        {"name": "node-2.example.com", "status": "warmup"},
    ]
    assert _json_lines(sections["couchbase_nodes_services"]) == [
        {"name": "node-1.example.com", "services": ["kv", "n1ql"]},
        {"name": "node-2.example.com"},
    ]
    assert _json_lines(sections["couchbase_nodes_ports"]) == [
        {"name": "node-1.example.com", "ports": {"direct": 11210}},
        {"name": "node-2.example.com"},
    ]
    assert _json_lines(sections["couchbase_nodes_stats"]) == [
        {"name": "node-1.example.com", "cpu_utilization_rate": 12.5, "mem_total": 1024},
        {"name": "node-2.example.com"},
    ]
    assert _json_lines(sections["couchbase_nodes_cache"]) == [
        {"name": "node-1.example.com", "get_hits": 3},
        {"name": "node-2.example.com"},
    ]
    assert _json_lines(sections["couchbase_nodes_items"]) == [
        {"name": "node-1.example.com", "curr_items": 7},
        {"name": "node-2.example.com"},
    ]
    assert _json_lines(sections["couchbase_nodes_size"]) == [
        {"name": "node-1.example.com"},
        {"name": "node-2.example.com"},
    ]


@responses.activate
def test_pool_without_nodes_yields_empty_sections(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json={})

    exit_code = _run([HOST])

    sections = _sections(capsys.readouterr().out)
    assert exit_code == 0
    assert set(sections) == {
        "couchbase_nodes_uptime",
        "couchbase_nodes_operations",
        "couchbase_nodes_info",
        "couchbase_nodes_services",
        "couchbase_nodes_ports",
        "couchbase_nodes_stats",
        "couchbase_nodes_cache",
        "couchbase_nodes_items",
        "couchbase_nodes_size",
        "couchbase_buckets_mem",
        "couchbase_buckets_operations",
        "couchbase_buckets_cache",
        "couchbase_buckets_vbuckets",
        "couchbase_buckets_fragmentation",
        "couchbase_buckets_items",
    }
    assert all(lines == [] for lines in sections.values())


@responses.activate
def test_bucket_sections_average_samples(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json={})
    responses.add(responses.GET, f"{BASE}/buckets/beer/stats", json=BUCKET_RESPONSE)

    _run(["-b", "beer", HOST])

    sections = _sections(capsys.readouterr().out)
    assert _json_lines(sections["couchbase_buckets_mem"]) == [{"name": "beer", "mem_total": 100.0}]
    assert _json_lines(sections["couchbase_buckets_operations"]) == [{"name": "beer", "ops": 2.0}]
    assert _json_lines(sections["couchbase_buckets_cache"]) == [
        {"name": "beer", "ep_cache_miss_rate": None}
    ]
    assert _json_lines(sections["couchbase_buckets_vbuckets"]) == [{"name": "beer"}]
    assert _json_lines(sections["couchbase_buckets_fragmentation"]) == [{"name": "beer"}]
    assert _json_lines(sections["couchbase_buckets_items"]) == [{"name": "beer"}]


@responses.activate
def test_bucket_without_samples_is_reported_with_name_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    responses.add(responses.GET, BASE, json={})
    responses.add(responses.GET, f"{BASE}/buckets/empty/stats", json={})

    _run(["-b", "empty", HOST])

    sections = _sections(capsys.readouterr().out)
    assert _json_lines(sections["couchbase_buckets_mem"]) == [{"name": "empty"}]


@responses.activate
def test_unreachable_bucket_is_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json={})
    responses.add(responses.GET, f"{BASE}/buckets/missing/stats", status=404)
    responses.add(responses.GET, f"{BASE}/buckets/present/stats", json=BUCKET_RESPONSE)

    exit_code = _run(["-b", "missing", "-b", "present", HOST])

    sections = _sections(capsys.readouterr().out)
    assert exit_code == 0
    assert [entry["name"] for entry in _json_lines(sections["couchbase_buckets_mem"])] == [
        "present"
    ]


@responses.activate
def test_bucket_with_invalid_json_is_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, json={})
    responses.add(responses.GET, f"{BASE}/buckets/broken/stats", body="not json")

    exit_code = _run(["-b", "broken", HOST])

    sections = _sections(capsys.readouterr().out)
    assert exit_code == 0
    assert sections["couchbase_buckets_mem"] == []


@responses.activate
def test_unreachable_bucket_raises_in_debug_mode() -> None:
    responses.add(responses.GET, BASE, json={})
    responses.add(responses.GET, f"{BASE}/buckets/missing/stats", status=500)

    with pytest.raises(requests.HTTPError):
        _run(["--debug", "-b", "missing", HOST])


@responses.activate
def test_unreachable_pool_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    responses.add(responses.GET, BASE, status=401)

    exit_code = _run([HOST])

    assert exit_code == 1
    assert capsys.readouterr().out == ""


@responses.activate
def test_pool_connection_error_returns_error_code() -> None:
    responses.add(responses.GET, BASE, body=requests.ConnectionError("refused"))

    assert _run([HOST]) == 1


@responses.activate
def test_pool_with_invalid_json_returns_error_code() -> None:
    responses.add(responses.GET, BASE, body="<html>login</html>")

    assert _run([HOST]) == 1


@responses.activate
def test_unreachable_pool_raises_in_debug_mode() -> None:
    responses.add(responses.GET, BASE, status=503)

    with pytest.raises(requests.HTTPError):
        _run(["--debug", HOST])


@responses.activate
def test_credentials_are_sent_as_basic_auth() -> None:
    responses.add(responses.GET, BASE, json={})

    _run(["-u", "admin", "--password", "secret", HOST])

    assert responses.calls[0].request.headers["Authorization"] == "Basic YWRtaW46c2VjcmV0"


@responses.activate
def test_without_username_no_auth_header_is_sent() -> None:
    responses.add(responses.GET, BASE, json={})

    _run([HOST])

    assert "Authorization" not in responses.calls[0].request.headers


@responses.activate
def test_port_is_used_for_api_calls() -> None:
    responses.add(responses.GET, f"http://{HOST}:9999/pools/default", json={})

    assert _run(["-P", "9999", HOST]) == 0


@responses.activate
def test_main_reads_command_line_from_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    responses.add(responses.GET, BASE, json={})
    monkeypatch.setattr(sys, "argv", ["agent_couchbase", HOST])

    assert agent_couchbase.main() == 0
