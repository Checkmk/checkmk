#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from dump_fastapi_openapi_spec import typescript_view, validate_openapi_3_2
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

UPDATE_REF = {"$ref": "#/components/schemas/Update"}
JSON_UPDATE = {
    "type": "string",
    "contentMediaType": "application/json",
    "contentSchema": UPDATE_REF,
}


def _spec(event_stream: object) -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "app", "version": "1"},
        "paths": {
            "/events": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "events",
                            "content": {"text/event-stream": event_stream},
                        }
                    }
                }
            }
        },
        "components": {"schemas": {"Update": {"type": "object"}}},
    }


def test_stream_item_with_json_data_becomes_the_response_schema() -> None:
    item = {"type": "object", "properties": {"event": {"const": "update"}, "data": JSON_UPDATE}}
    decoded_item = {
        "type": "object",
        "properties": {"event": {"const": "update"}, "data": UPDATE_REF},
    }

    view = typescript_view(_spec({"itemSchema": {"oneOf": [item]}}))

    assert view == _spec({"schema": {"oneOf": [decoded_item]}})


def test_data_with_another_content_media_type_stays_encoded() -> None:
    yaml_data = {
        "type": "string",
        "contentMediaType": "application/yaml",
        "contentSchema": UPDATE_REF,
    }

    view = typescript_view(_spec({"itemSchema": yaml_data}))

    assert view == _spec({"schema": yaml_data})


def test_spec_without_item_schema_is_unchanged() -> None:
    spec = _spec({"schema": UPDATE_REF})

    assert typescript_view(spec) == spec


def test_view_is_an_openapi_3_1_document() -> None:
    spec = {**_spec({"schema": UPDATE_REF}), "openapi": "3.2.0"}

    assert typescript_view(spec) == _spec({"schema": UPDATE_REF})


def test_item_schema_outside_response_content_is_unchanged() -> None:
    spec = _spec({"schema": UPDATE_REF})
    spec["components"] = {
        "schemas": {"Feed": {"itemSchema": {"properties": {"data": JSON_UPDATE}}}}
    }

    assert typescript_view(spec) == spec


def test_media_type_with_schema_and_item_schema_is_rejected() -> None:
    with pytest.raises(
        ValueError, match="GET /events 200 text/event-stream has both a schema and an itemSchema"
    ):
        typescript_view(_spec({"schema": {"type": "string"}, "itemSchema": UPDATE_REF}))


def test_openapi_3_2_document_with_stream_items_is_valid() -> None:
    item = {"type": "object", "properties": {"event": {"const": "update"}, "data": JSON_UPDATE}}

    validate_openapi_3_2({**_spec({"itemSchema": item}), "openapi": "3.2.0"})


def test_openapi_3_1_document_is_rejected() -> None:
    with pytest.raises(ValueError, match="build the app with cmk.fastapi.FastAPI"):
        validate_openapi_3_2(_spec({"schema": UPDATE_REF}))


def test_invalid_openapi_3_2_document_is_rejected() -> None:
    spec = {**_spec({"schema": UPDATE_REF}), "openapi": "3.2.0", "info": {"title": "app"}}

    with pytest.raises(OpenAPIValidationError, match="'version' is a required property"):
        validate_openapi_3_2(spec)
