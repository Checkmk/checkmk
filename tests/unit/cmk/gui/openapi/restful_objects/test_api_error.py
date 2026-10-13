#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from cmk.gui.openapi.restful_objects.api_error import api_custom_error_schema


def test_api_custom_error_schema_is_memoized() -> None:
    assert api_custom_error_schema(
        HTTPStatus.NOT_FOUND, "Host not found"
    ) is api_custom_error_schema(HTTPStatus.NOT_FOUND, "Host not found")


def test_api_custom_error_schema_names_are_unique_and_deterministic() -> None:
    first = api_custom_error_schema(HTTPStatus.NOT_FOUND, "Host not found")
    second = api_custom_error_schema(HTTPStatus.NOT_FOUND, "Service not found")

    assert first.__name__ != second.__name__
    assert first.__name__ == "Api404CustomError34BAC53CD7F25220"
