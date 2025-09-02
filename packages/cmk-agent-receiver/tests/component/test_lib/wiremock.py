#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from collections.abc import Mapping
from http import HTTPMethod
from typing import Literal

import httpx

UrlType = Literal["url", "urlPath", "urlPatter,", "urlPathPattern"]
PatternType = Literal["matchesJsonSchema", "equalTo", "matchesJsonSchema"]


@dataclasses.dataclass
class Request:
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url_type: UrlType
    url: str
    body_patterns: list[Mapping[PatternType, str]] | None = None
    query_parameters: Mapping[str, Mapping[PatternType, str]] | None = None

    def as_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"method": self.method, self.url_type: self.url}
        if self.query_parameters:
            d["queryParameters"] = self.query_parameters
        if self.body_patterns:
            d["bodyPatterns"] = self.body_patterns
        return d


@dataclasses.dataclass
class Response:
    status: int
    body: str
    headers: Mapping[str, str]

    def as_dict(self) -> Mapping[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class WMapping:
    # See: https://wiremock.org/docs/standalone/admin-api-reference/#tag/Stub-Mappings
    request: Request
    response: Response
    priority: int = 1

    def as_dict(self) -> Mapping[str, object]:
        return {"request": self.request.as_dict(), "response": self.response.as_dict()}


@dataclasses.dataclass
class Wiremock:
    port: int
    wiremock_hostname: str

    @property
    def base_url(self) -> str:
        return f"http://{self.wiremock_hostname}:{self.port}"

    def setup_mapping(
        self,
        mapping: WMapping,
    ) -> None:
        response = httpx.post(
            f"{self.base_url}/__admin/mappings",
            json=mapping.as_dict(),
            timeout=1,
        )
        response.raise_for_status()

    def get_all_url_path_requests(self, url_path: str, method: HTTPMethod) -> list[dict]:
        query = {
            "urlPathPattern": url_path,
            "method": method,
        }

        response = httpx.post(
            f"{self.base_url}/__admin/requests/find",
            json=query,
            timeout=1,
        )
        response.raise_for_status()

        all_requests = response.json()["requests"]
        return list(all_requests)
