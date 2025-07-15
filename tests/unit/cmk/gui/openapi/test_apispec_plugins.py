#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest
from apispec import APISpec
from marshmallow import post_load, Schema, ValidationError

from cmk.gui.fields.base import ValueTypedDictSchema
from cmk.gui.openapi.spec.plugin_marshmallow import CheckmkMarshmallowPlugin

from cmk import fields


class Movie:
    def __init__(self, title: str, director: str, year: int) -> None:
        self.title = title
        self.director = director
        self.year = year

    def __repr__(self) -> str:
        return f"<Movie(title={self.title!r}, director={self.director!r}, year={self.year})>"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Movie):
            return NotImplemented
        return self.year > other.year

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Movie)
            and self.title == other.title
            and self.director == other.director
            and self.year == other.year
        )


MOVIES = {
    "Solyaris": {
        "title": "Solyaris",
        "director": "Andrei Tarkovsky",
        "year": 1972,
    },
    "Stalker": {
        "title": "Stalker",
        "director": "Andrei Tarkovsky",
        "year": 1979,
    },
}

BROKEN_MOVIE = {
    "Plan 9 from Outer Space": {
        "title": None,
        "director": None,
        "year": 1957,
    },
}

EXPECTED_MOVIES = {
    "Solyaris": Movie(
        title="Solyaris",
        director="Andrei Tarkovsky",
        year=1972,
    ),
    "Stalker": Movie(
        title="Stalker",
        director="Andrei Tarkovsky",
        year=1979,
    ),
}


class MovieSchema(Schema):
    title = fields.String(required=True)
    director = fields.String(required=True)
    year = fields.Integer(required=True)

    @post_load
    def make_movie(self, data, **kwargs):
        return Movie(**data)


class MovieDictSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = MovieSchema


class CustomTagDictSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(
            fields.String(
                description="Tag value here",
                pattern="foo|bar",
                required=True,
            )
        )


class IntegerDictSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(fields.Integer())


class EmailSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(fields.Email())


class EmailWithStaticFieldSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(fields.Email())

    owner = fields.Email(required=True, description="The owner of the contact")


class MovieWithStaticFieldSchema(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = MovieSchema

    best_movie = fields.Nested(MovieSchema, description="The best movie ever made")


@pytest.fixture(name="spec", scope="function")
def spec_fixture():
    return APISpec(
        title="Sensationalist Witty Title",
        version="1.0.0",
        openapi_version="3.0.0",
        plugins=[
            CheckmkMarshmallowPlugin(),
        ],
    )


def test_apispec_plugin_string_to_schema_dict(spec: APISpec) -> None:
    # Schema suffix of schemas gets stripped by library
    spec.components.schema("MovieDict", schema=MovieDictSchema)

    schemas = spec.to_dict()["components"]["schemas"]
    assert schemas["MovieDict"] == {
        "type": "object",
        "additionalProperties": {"$ref": "#/components/schemas/Movie"},
    }


def test_apispec_plugin_string_to_string_dict(spec: APISpec) -> None:
    # Schema suffix of schemas gets stripped by library
    spec.components.schema("CustomTagDict", schema=CustomTagDictSchema)
    schemas = spec.to_dict()["components"]["schemas"]
    assert schemas["CustomTagDict"] == {
        "type": "object",
        "additionalProperties": {
            "type": "string",
            "description": "Tag value here",
            "pattern": "foo|bar",
            "required": True,
        },
    }


def test_apispec_plugin_parameters(spec: APISpec) -> None:
    # Different code paths are executed here. We need to make sure our plug-in handles this.
    spec.components.parameter("var", "path", {"description": "Some path variable"})


@pytest.mark.parametrize(
    ["schema_class", "in_data", "expected_result"],
    [
        (MovieDictSchema, MOVIES, EXPECTED_MOVIES),
        (IntegerDictSchema, {"foo": 1}, {"foo": 1}),
        (EmailSchema, {"bob": "bob@example.com"}, {"bob": "bob@example.com"}),
    ],
)
def test_typed_dictionary_success(
    schema_class: type[Schema],
    in_data: Mapping[str, object],
    expected_result: Mapping[str, object],
) -> None:
    schema = schema_class()
    result = schema.load(in_data)
    assert result == expected_result
    assert schema.dump(result) == in_data


@pytest.mark.parametrize(
    ["schema_class", "in_data"],
    [
        (MovieDictSchema, BROKEN_MOVIE),
        (IntegerDictSchema, {"bar": "eins"}),
        (EmailSchema, {"hans": "foo"}),
    ],
)
def test_typed_dictionary_failed_validation(
    schema_class: type[Schema], in_data: Mapping[str, object]
) -> None:
    schema = schema_class()
    with pytest.raises(ValidationError):
        schema.load(in_data)


def test_static_fields_and_wrapped_field() -> None:
    schema = EmailWithStaticFieldSchema()
    src_data = {"owner": "owner@example.com", "extra": "extra@example.com"}

    result = schema.load(src_data)
    assert result == src_data
    assert schema.dump(result) == src_data


def test_static_fields_and_schema() -> None:
    schema = MovieWithStaticFieldSchema()

    best_movie = {
        "title": "Back to the future",
        "director": "Robert Zemeckis",
        "year": 1985,
    }

    src_data: dict = {"best_movie": best_movie}
    src_data.update(MOVIES)

    result = schema.load(src_data)
    assert isinstance(result, dict)
    assert set(result) == set(src_data)
    assert schema.dump(result) == src_data


def test_invalid_data_type() -> None:
    schema = MovieDictSchema()
    with pytest.raises(ValidationError):
        schema.load("invalid_data")  # type: ignore[arg-type]
