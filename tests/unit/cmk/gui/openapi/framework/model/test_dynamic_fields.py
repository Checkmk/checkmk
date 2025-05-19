#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import datetime
import json

from pydantic import TypeAdapter

from cmk.gui.openapi.framework.model import json_dump_without_omitted
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields

_DT_2025 = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)


@dataclasses.dataclass
class _TestModel(WithDynamicFields):
    field: int


def test_dynamic_field_serialization() -> None:
    model = _TestModel(
        field=123,
        dynamic_fields={
            "extra_field": "extra_value",
            "other_type": _DT_2025,
        },
    )

    result = TypeAdapter(_TestModel).dump_json(model)  # nosemgrep: type-adapter-detected
    # to not rely on the key order, we compare the loaded json
    assert json.loads(result) == {
        "field": 123,
        "extra_field": "extra_value",
        "other_type": "2025-01-01T00:00:00Z",
    }


def test_dynamic_field_serialization_without_omitted() -> None:
    # we need to make sure this works with the `json_dump_without_omitted` function
    model = _TestModel(
        field=123,
        dynamic_fields={
            "extra_field": "extra_value",
            "other_type": _DT_2025,
        },
    )

    result = json.loads(json_dump_without_omitted(_TestModel, model))
    assert result == {
        "field": 123,
        "extra_field": "extra_value",
        "other_type": "2025-01-01T00:00:00Z",
    }


def test_dynamic_field_deserialization() -> None:
    adapter = TypeAdapter(_TestModel)  # nosemgrep: type-adapter-detected
    model = adapter.validate_python(
        {
            "field": 123,
            "extra_field": "extra_value",
            "other_type": _DT_2025,
        }
    )
    assert model.field == 123
    assert model.dynamic_fields["extra_field"] == "extra_value"
    assert model.dynamic_fields["other_type"] == _DT_2025


@dataclasses.dataclass
class _NestedModel:
    nested: _TestModel
    nested_list: list[_TestModel]


def test_dynamic_field_serialization_nested() -> None:
    model = _NestedModel(
        nested=_TestModel(
            field=123,
            dynamic_fields={
                "other_type": _DT_2025,
            },
        ),
        nested_list=[
            _TestModel(
                field=456,
                dynamic_fields={
                    "extra_field": "extra_value",
                },
            )
        ],
    )

    result = TypeAdapter(_NestedModel).dump_json(model)  # nosemgrep: type-adapter-detected
    # to not rely on the key order, we compare the loaded json
    assert json.loads(result) == {
        "nested": {"field": 123, "other_type": "2025-01-01T00:00:00Z"},
        "nested_list": [{"field": 456, "extra_field": "extra_value"}],
    }


def test_dynamic_field_serialization_nested_without_omitted() -> None:
    # we need to make sure this works with the `json_dump_without_omitted` function
    model = _NestedModel(
        nested=_TestModel(
            field=123,
            dynamic_fields={
                "other_type": _DT_2025,
            },
        ),
        nested_list=[
            _TestModel(
                field=456,
                dynamic_fields={
                    "extra_field": "extra_value",
                },
            )
        ],
    )

    result = json.loads(json_dump_without_omitted(_NestedModel, model))
    assert result == {
        "nested": {"field": 123, "other_type": "2025-01-01T00:00:00Z"},
        "nested_list": [{"field": 456, "extra_field": "extra_value"}],
    }


def test_dynamic_field_deserialization_nested() -> None:
    adapter = TypeAdapter(_NestedModel)  # nosemgrep: type-adapter-detected
    model = adapter.validate_python(
        {
            "nested": {
                "field": 123,
                "other_type": _DT_2025,
            },
            "nested_list": [
                {
                    "field": 456,
                    "extra_field": "extra_value",
                }
            ],
        }
    )
    assert model.nested.field == 123
    assert model.nested.dynamic_fields["other_type"] == _DT_2025
    assert len(model.nested_list) == 1
    assert model.nested_list[0].field == 456
    assert model.nested_list[0].dynamic_fields["extra_field"] == "extra_value"


def test_json_schema_dynamic_field() -> None:
    model = TypeAdapter(_TestModel)  # nosemgrep: type-adapter-detected
    schema = model.json_schema()
    # the `WithDynamicFields` class should only add the `additionalProperties` key
    # properties and required must not change
    assert schema["type"] == "object"
    assert schema["title"] == "_TestModel"
    assert "field" in schema["properties"]
    assert len(schema["properties"]) == 1, (
        f"Expected only `field` in properties: {schema['properties']}"
    )
    assert schema["required"] == ["field"]
    # no specific type for dynamic fields set, default should be `object`
    assert schema["additionalProperties"]["type"] == "object"


def test_json_schema_dynamic_field_custom_type() -> None:
    @dataclasses.dataclass(kw_only=True)
    class _CustomType(WithDynamicFields):
        field: int
        dynamic_fields: dict[str, str] = dataclasses.field(
            metadata={
                "title": "custom_title",
                "description": "custom_description",
                "examples": ["custom_example"],
            },
        )

    model = TypeAdapter(_CustomType)  # nosemgrep: type-adapter-detected
    schema = model.json_schema()
    assert "dynamic_fields" not in schema["properties"]
    assert "dynamic_fields" not in schema["required"]
    assert schema["additionalProperties"]["type"] == "string"
    assert schema["additionalProperties"]["title"] == "custom_title"
    assert schema["additionalProperties"]["description"] == "custom_description"
    assert schema["additionalProperties"]["examples"] == ["custom_example"]
