#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import Literal

import httpx
from pydantic import BaseModel, Field

PatternType = Literal["matchesJsonSchema", "equalTo", "matches", "equalToJson"]
AllowedHeader = Literal["Content-Type", "Authorization"]


class Request(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url: str
    bodyPatterns: list[Mapping[PatternType, str]] | None = None
    queryParameters: Mapping[str, Mapping[PatternType, str]] | None = None
    headers: Mapping[AllowedHeader, Mapping[PatternType, str]] = Field(default_factory=dict)


class Response(BaseModel):
    status: int
    body: str | None = None
    headers: Mapping[str, str] = Field(default_factory=dict)


class WMapping(BaseModel):
    # See: https://wiremock.org/docs/standalone/admin-api-reference/#tag/Stub-Mappings
    request: Request
    response: Response
    priority: int = 1
    scenarioName: str | None = None
    requiredScenarioState: str | None = None
    newScenarioState: str | None = None


class Wiremock(BaseModel):
    port: int
    wiremock_hostname: str

    @property
    def base_url(self) -> str:
        return f"http://{self.wiremock_hostname}:{self.port}"

    @property
    def admin_url(self) -> str:
        return f"{self.base_url}/__admin"

    def reset(self) -> None:
        resp = httpx.delete(f"{self.admin_url}/mappings")
        assert resp.status_code == HTTPStatus.OK

    def setup_mapping(
        self,
        mapping: WMapping,
    ) -> None:
        response = httpx.post(
            f"{self.admin_url}/mappings",
            json=mapping.model_dump(exclude_none=True),
            timeout=1,
        )
        assert response.status_code < 400, response.text

    def get_all_url_path_requests(self, url_path: str, method: HTTPMethod) -> list[dict]:
        query = {
            "urlPathPattern": url_path,
            "method": method,
        }

        response = httpx.post(
            f"{self.admin_url}/requests/find",
            json=query,
            timeout=1,
        )
        assert response.status_code < 400, response.text

        all_requests = response.json()["requests"]
        return list(all_requests)
