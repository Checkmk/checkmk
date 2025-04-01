#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import NotRequired, TypedDict

import pytest

from cmk.gui.openapi.framework.model import api_field


class _OptionalKwOnly(TypedDict):
    kw_only: NotRequired[bool]


@pytest.mark.parametrize(
    "class_kwargs, field_kwargs, expected",
    [
        ({}, {}, False),
        ({"kw_only": True}, {}, True),
        ({"kw_only": False}, {}, False),
        ({}, {"kw_only": True}, True),
        ({}, {"kw_only": False}, False),
        ({"kw_only": True}, {"kw_only": False}, False),
        ({"kw_only": False}, {"kw_only": True}, True),
    ],
)
def test_keyword_only(
    class_kwargs: _OptionalKwOnly, field_kwargs: _OptionalKwOnly, expected: bool
) -> None:
    @dataclasses.dataclass(**class_kwargs)
    class TestModel:
        field: str = api_field(description="test", **field_kwargs)

    field = dataclasses.fields(TestModel)[0]
    assert field.kw_only == expected


def test_default() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(description="test", default="foo")

    field = dataclasses.fields(TestModel)[0]
    assert field.default == "foo"
    assert field.default_factory is dataclasses.MISSING


def test_default_factory() -> None:
    def default_factory() -> str:
        return "foo"

    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(description="test", default_factory=default_factory)

    field = dataclasses.fields(TestModel)[0]
    assert field.default == dataclasses.MISSING
    assert field.default_factory == default_factory


def test_mutually_exclusive_default() -> None:
    with pytest.raises(ValueError, match="default and default_factory"):
        api_field(description="test", default="foo", default_factory=lambda: "bar")  # type: ignore[call-overload]


def test_metadata() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(
            title="title",
            description="description",
            example="example",
            additional_metadata={"extra": "metadata"},
        )

    field = dataclasses.fields(TestModel)[0]
    assert field.metadata["title"] == "title"
    assert field.metadata["description"] == "description"
    # special case: example will be converted to examples
    assert "example" not in field.metadata
    assert field.metadata["examples"] == ["example"]
    assert field.metadata["extra"] == "metadata"
