# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers for tests against a faked Nutanix v4 API"""

import base64
from collections.abc import Callable, Sequence

from requests import PreparedRequest
from responses import matchers

SERVER = "prism.example.com"
BASE_URL = f"https://{SERVER}:9440"
USERNAME = "monitoring"
PASSWORD = "secret"
BASIC_AUTH = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

type Matcher = Callable[[PreparedRequest], tuple[bool, str]]


def v4_url(path: str) -> str:
    return f"{BASE_URL}/api/{path}"


def page(entities: Sequence[object], *, has_next: bool) -> dict[str, object]:
    links = [{"rel": "self", "href": "ignored"}]
    if has_next:
        links.append({"rel": "next", "href": "ignored"})
    return {"data": list(entities), "metadata": {"links": links}}


def page_matcher(page_number: int) -> Matcher:
    return matchers.query_param_matcher(
        {"$page": str(page_number), "$limit": "100"}, strict_match=False
    )


def with_basic_auth() -> Matcher:
    return matchers.header_matcher({"Authorization": BASIC_AUTH})


def without_basic_auth(request: PreparedRequest) -> tuple[bool, str]:
    if "Authorization" in request.headers:
        return False, "the request sends the password"
    return True, ""


class FakeStorage:
    def __init__(self) -> None:
        self.entries: dict[str, str] = {}

    def read[T](self, key: str, default: T) -> str | T:
        return self.entries.get(key, default)

    def write(self, key: str, content: str) -> None:
        self.entries[key] = content


# Error bodies as recorded on Prism Central 7.5 (lab 2)
VM_NOT_FOUND = {
    "data": {
        "error": [
            {
                "message": "Failed to perform the operation on the VM with UUID 'vm0', "
                "because it is not found.",
                "severity": "ERROR",
                "code": "VMM-30100",
                "$objectType": "vmm.v4.error.AppMessage",
            }
        ],
        "$objectType": "vmm.v4.error.ErrorResponse",
    }
}
LIMIT_TOO_LARGE = {
    "data": {
        "error": {
            "validationErrorMessages": [
                {
                    "location": "@query.$limit",
                    "message": "Numeric instance is greater than the required maximum "
                    "(maximum: 100, found: 500)",
                }
            ],
            "error": "Bad Request",
            "statusCode": 400,
            "$objectType": "clustermgmt.v4.error.SchemaValidationError",
        },
        "$objectType": "clustermgmt.v4.error.ErrorResponse",
    }
}
LOGIN_REJECTED = {"message": "invalid credentials"}
