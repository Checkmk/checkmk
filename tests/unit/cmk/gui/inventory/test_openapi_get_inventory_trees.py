#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tests.testlib.unit.rest_api_client import RequestHandler, Response, RestApiException

from tests.unit.cmk.web_test_app import WebTestAppForCMK, WebTestAppRequestHandler

import cmk.ccc.store

import cmk.utils.paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.http import HTTPMethod

JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


class _InventoryClient:
    def __init__(self, request_handler: RequestHandler, url_prefix: str):
        self.request_handler = request_handler
        self._url_prefix = url_prefix

    def _get_redirect_url(self, location_header: str) -> str:
        prefix = urllib.parse.urlparse(self._url_prefix)
        location = urllib.parse.urlparse(location_header)
        return urllib.parse.urlunparse(
            (
                location.scheme or prefix.scheme,
                location.netloc or prefix.netloc,
                location.path,
                location.params,
                location.query,
                location.fragment,
            )
        )

    # This is public for quick debugging sessions
    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, Any] | None = None,
    ) -> Response:
        default_headers: Mapping[str, str] = JSON_HEADERS
        url = self._url_prefix + url
        resp = self.request_handler.request(
            method=method,
            url=url,
            query_params=query_params,
            body=None,
            headers=default_headers,
            follow_redirects=False,  # we handle redirects ourselves
        )
        if resp.status_code >= 400:
            raise RestApiException(
                url, method, None, default_headers, resp, query_params=query_params
            )
        return resp

    def get_all(self, host_names: list[str]) -> Response:
        return self.request(
            "get",
            url="/domain-types/inventory/collections/all",
            query_params={"host_names": host_names},
        )


def test_openapi_get_inventory_trees(
    tmp_path: Path,
    mock_livestatus: MockLiveStatusConnection,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query(
        [
            "GET hosts",
            "Columns: host_structured_status",
            "Filter: host_name = hostname1",
        ],
        sites=["NO_SITE"],
    )
    cmk.ccc.store.save_object_to_file(
        cmk.utils.paths.omd_root / "var/check_mk/inventory/hostname1",
        {
            "Attributes": {"Pairs": {"key": "value1"}},
            "Table": {
                "KeyColumns": ["column"],
                "Rows": [{"column": "col-value2"}],
            },
            "Nodes": {
                "nodename": {
                    "Attributes": {"Pairs": {"n-key": "n-value3"}},
                    "Table": {
                        "KeyColumns": ["n-column"],
                        "Rows": [{"n-column": "n-col-value4"}],
                    },
                    "Nodes": {},
                }
            },
        },
    )

    with live():
        resp = _InventoryClient(
            WebTestAppRequestHandler(aut_user_auth_wsgi_app),
            "/NO_SITE/check_mk/api/unstable",
        ).get_all(host_names=["hostname1", "hostname2"])
        resp.assert_status_code(200)
        assert resp.json == {
            "domainType": "inventory",
            "id": "inventory_trees",
            "links": [
                {
                    "domainType": "link",
                    "href": "http://localhost/NO_SITE/check_mk/api/1.0/domain-types/inventory/collections/all",
                    "method": "GET",
                    "rel": "self",
                    "type": "application/json",
                }
            ],
            "value": [
                {
                    "host_name": "hostname1",
                    "inventory_tree": {
                        "attributes": {"pairs": {"key": "value1"}},
                        "table": {
                            "key_columns": ["column"],
                            "rows": [{"column": "col-value2"}],
                        },
                        "nodes": {
                            "nodename": {
                                "attributes": {"pairs": {"n-key": "n-value3"}},
                                "table": {
                                    "key_columns": ["n-column"],
                                    "rows": [{"n-column": "n-col-value4"}],
                                },
                                "nodes": {},
                            }
                        },
                    },
                }
            ],
        }
