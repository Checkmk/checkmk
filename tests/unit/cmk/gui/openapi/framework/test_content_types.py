#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import pytest

from cmk.gui.openapi.framework.content_types import (
    ContentTypeConverter,
    convert_request_body,
    get_converter_annotation,
)


def _to_string(body: bytes, content_type: str) -> str:
    return content_type + ":" + body.decode("utf-8")


_TestModel = Annotated[str, ContentTypeConverter(_to_string)]


def test_get_converter_annotation() -> None:
    assert get_converter_annotation(str) is None
    assert isinstance(get_converter_annotation(_TestModel), ContentTypeConverter)


def test_convert_request_body_json_default() -> None:
    body = b'{"test": 123}'
    content_type = "application/json"

    # body_model only matters for retrieving the converter,
    # so could be anything as long as there is no annotation
    result = convert_request_body(body_model=int, content_type=content_type, body=body)
    assert result == {"test": 123}, "Expected to default to JSON decoding"


def test_convert_request_body_custom() -> None:
    body = b'{"test": 123}'
    content_type = "application/json"

    result = convert_request_body(body_model=_TestModel, content_type=content_type, body=body)
    assert result == 'application/json:{"test": 123}', "Expected to use custom converter function"


def test_convert_request_body_unknown_content_type() -> None:
    body = b"123"
    content_type = "image/gif"

    with pytest.raises(Exception, match="Unsupported content type: image/gif"):
        convert_request_body(body_model=int, content_type=content_type, body=body)
