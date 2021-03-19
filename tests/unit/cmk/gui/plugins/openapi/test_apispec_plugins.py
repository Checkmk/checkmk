#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from apispec import APISpec  # type: ignore[import]
from marshmallow import Schema, fields, post_load

from cmk.gui.plugins.openapi.plugins import ValueTypedDictSchema, ValueTypedDictMarshmallowPlugin


class Movie:
    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)
        self.kw = kw
        self.value = tuple(sorted(kw.items()))

    def __repr__(self):
        return "<Movie %r>" % (self.kw,)

    def __lt__(self, other):
        return self.kw['year'] > other.kw['year']

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.value == other.value


MOVIES = {
    'Solyaris': {
        'director': 'Andrei Tarkovsky',
        'year': 1972
    },
    'Stalker': {
        'director': 'Andrei Tarkovsky',
        'year': 1979
    },
}

EXPECTED_MOVIES = [
    Movie(director='Andrei Tarkovsky', year=1972, title='Solyaris'),
    Movie(director='Andrei Tarkovsky', year=1979, title='Stalker'),
]


class MovieSchema(Schema):
    title = fields.String(required=True)
    director = fields.String(required=True)
    year = fields.Integer(required=True)

    @post_load
    def make_movie(self, data, **kwargs):
        return Movie(**data)


class MoviesSchema(ValueTypedDictSchema):
    key_name = 'title'
    keep_key = False
    value_type = MovieSchema


@pytest.fixture(name="spec")
def spec_fixture():
    return APISpec(title='Sensationalist Witty Title',
                   version='1.0.0',
                   openapi_version='3.0.0',
                   plugins=[
                       ValueTypedDictMarshmallowPlugin(),
                   ])


def test_apispec_plugin_parameters(spec):
    # Different code paths are executed here. We need to make sure our plugin handles this.
    spec.components.parameter('var', 'path', {'description': "Some path variable"})


def test_apispec_plugin_value_typed_dict(spec):
    # Schema suffix of schemas gets stripped by library
    spec.components.schema('Movies', schema=MoviesSchema)

    schemas = spec.to_dict()['components']['schemas']
    assert schemas['Movies'] == {
        u'type': u'object',
        u'additionalProperties': {
            '$ref': '#/components/schemas/Movie'
        }
    }


def test_apispec_load():
    result = MoviesSchema().load(MOVIES)
    assert sorted(result) == sorted(EXPECTED_MOVIES)


def test_apispec_dump():
    result = MoviesSchema().dump(EXPECTED_MOVIES)
    assert result == MOVIES
