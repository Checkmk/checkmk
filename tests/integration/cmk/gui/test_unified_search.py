#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Generator

import pytest
from requests import Response

from cmk.gui.search.type_defs import Provider
from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


@pytest.fixture
def session(site: Site) -> Generator[CMKWebSession]:
    session = CMKWebSession(site)
    session.login()
    yield session
    session.logout()


def test_result_counts_of_different_search_queries(session: CMKWebSession) -> None:
    client = _SearchClient(session)

    # There is at least one result when querying "host"
    host_query_resp = client.search("host")
    host_result_count = _get_result_count(host_query_resp)
    assert host_result_count

    # A more specific query like "host groups" leads to fewer results
    host_groups_query_resp = client.search("host groups")
    host_groups_result_count = _get_result_count(host_groups_query_resp)
    assert host_groups_result_count and host_groups_result_count < host_result_count

    # Specifying a provider i.e. "monitoring" leads to fewer results
    host_with_provider_query_resp = client.search("host", provider="monitoring")
    host_with_provider_result_count = _get_result_count(host_with_provider_query_resp)
    assert host_with_provider_result_count and host_with_provider_result_count < host_result_count


def test_result_payload_shape_and_metadata(session: CMKWebSession) -> None:
    resp_json = _SearchClient(session).search("host").json()

    # Assert the shape of the payload
    assert "result" in resp_json
    for result_key in ("url", "query", "counts", "results"):
        assert result_key in resp_json["result"], f"{result_key!r} is missing."
    for count_key in ("total", "setup", "monitoring", "customize"):
        assert count_key in resp_json["result"]["counts"], f"{count_key!r} is missing."
    assert isinstance(resp_json["result"]["results"], list)

    # Check that metadata is correctly formatted
    assert "ajax_unified_search.py?q=host&provider=all" in resp_json["result"]["url"]
    assert resp_json["result"]["query"] == "host"


@dataclasses.dataclass
class _SearchClient:
    _session: CMKWebSession

    def search(self, query: str, provider: Provider | None = None) -> Response:
        return self._session.get(f"ajax_unified_search.py?q={query}&provider={provider or 'all'}")


def _get_result_count(resp: Response) -> int:
    return int(resp.json()["result"]["counts"]["total"])
