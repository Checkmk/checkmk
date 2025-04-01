#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Annotated, cast

import pytest
from pydantic import PlainSerializer

from cmk.gui.openapi.framework.handler import _dump_response, _strip_annotated
from cmk.gui.openapi.framework.model import ApiOmitted


@pytest.mark.parametrize(
    "annotated, expected",
    [
        pytest.param(Annotated[int, "foo"], int, id="simple"),
        pytest.param(Annotated[Annotated[int, "foo"], "bar"], int, id="nested"),
        pytest.param(
            Annotated[dict[str, Annotated[int, "foo"]], "bar"],
            dict[str, Annotated[int, "foo"]],
            id="only_outer",
        ),
    ],
)
def test_strip_annotated(annotated: type, expected: type) -> None:
    assert _strip_annotated(annotated) == expected


@dataclass
class _TestResponse:
    field: int


@dataclass
class _TestResponseOmitted:
    field: int
    omitted: str | ApiOmitted = ApiOmitted()


def test_dump_response_empty() -> None:
    result = _dump_response(None, None)
    assert result is None


def test_dump_response_simple() -> None:
    result = _dump_response(_TestResponse(field=123), _TestResponse)
    assert result == {"field": 123}


def test_dump_response_omitted() -> None:
    result = _dump_response(_TestResponseOmitted(field=123), _TestResponseOmitted)
    assert result == {"field": 123}
    result = _dump_response(_TestResponseOmitted(field=123, omitted="no"), _TestResponseOmitted)
    assert result == {"field": 123, "omitted": "no"}


def test_dump_response_annotated() -> None:
    result = _dump_response(
        _TestResponse(field=123), cast(type[_TestResponse], Annotated[_TestResponse, "foo"])
    )
    assert result == {"field": 123}


def test_dump_response_pydantic_annotated() -> None:
    def _serializer(value: _TestResponse) -> dict:
        # both aliasing and changing types work
        return {"custom_name": str(value.field * 2)}

    result = _dump_response(
        _TestResponse(field=123),
        cast(type[_TestResponse], Annotated[_TestResponse, PlainSerializer(_serializer)]),
    )
    assert result == {"custom_name": "246"}
