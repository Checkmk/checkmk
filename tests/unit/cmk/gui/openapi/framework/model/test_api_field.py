#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Literal, NotRequired, TypedDict

import pytest
from pydantic import TypeAdapter, ValidationError

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


def test_pattern() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(description="test", pattern="foo")

    adapter = TypeAdapter(TestModel)  # nosemgrep: type-adapter-detected
    schema = adapter.json_schema()
    assert "pattern" in schema["properties"]["field"]

    with pytest.raises(ValidationError, match="String should match pattern"):
        adapter.validate_python({"field": "invalid"})


def test_discriminator() -> None:
    @dataclasses.dataclass(kw_only=True, slots=True)
    class OptionOne:
        option_type: Literal["one"] = api_field(description="one")
        foo: str = api_field(description="foo")

    @dataclasses.dataclass(kw_only=True, slots=True)
    class OptionTwo:
        option_type: Literal["two"] = api_field(description="two")
        bar: int = api_field(description="bar")

    @dataclasses.dataclass
    class TestModel:
        field: OptionOne | OptionTwo = api_field(description="test", discriminator="option_type")

    adapter = TypeAdapter(TestModel)  # nosemgrep: type-adapter-detected
    schema = adapter.json_schema()
    assert schema["properties"]["field"]["discriminator"]["propertyName"] == "option_type"
    assert set(schema["properties"]["field"]["discriminator"]["mapping"]) == {"one", "two"}

    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_python({"field": {"option_type": "one"}})

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["type"] == "missing"
    assert errors[0]["loc"] == ("field", "one", "foo")


def test_metadata() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(
            alias="alias",
            title="title",
            description="description",
            example="example",
            additional_metadata={"extra": "metadata"},
        )

    field = dataclasses.fields(TestModel)[0]
    assert field.metadata["alias"] == "alias"
    assert field.metadata["title"] == "title"
    assert field.metadata["description"] == "description"
    # special case: example will be converted to examples
    assert "example" not in field.metadata
    assert field.metadata["examples"] == ["example"]
    assert field.metadata["extra"] == "metadata"


def test_json_schema_metadata() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(
            alias="alias",
            title="title",
            description="description",
            example="example",
            additional_metadata={"extra": "metadata"},
        )

    adapter = TypeAdapter(TestModel)  # nosemgrep: type-adapter-detected
    schema = adapter.json_schema()
    properties = schema["properties"]
    assert "field" not in properties
    assert "alias" in properties
    assert properties["alias"] == {
        "type": "string",
        "title": "title",
        "description": "description",
        "examples": ["example"],
    }


def test_alias_serialization() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(description="test", alias="alias")

    adapter = TypeAdapter(TestModel)  # nosemgrep: type-adapter-detected
    assert adapter.dump_python(TestModel(field="foo"), by_alias=True) == {"alias": "foo"}


def test_alias_deserialization() -> None:
    @dataclasses.dataclass
    class TestModel:
        field: str = api_field(description="test", alias="alias")

    adapter = TypeAdapter(TestModel)  # nosemgrep: type-adapter-detected
    assert adapter.validate_python({"alias": "foo"}) == TestModel(field="foo")

    with pytest.raises(ValidationError, match="type=missing"):
        adapter.validate_python({"field": "foo"})
