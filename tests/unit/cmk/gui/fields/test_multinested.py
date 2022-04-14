#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import random

import pytest
from marshmallow import fields, INCLUDE, post_load, ValidationError

from cmk.gui.fields.base import BaseSchema, MultiNested


class Schema(BaseSchema):
    cast_to_dict = True

    def __init__(self, required, *args, **kwargs):
        self.required = required
        super().__init__(*args, **kwargs)

    @post_load
    def _validate(self, data, many=False, partial=None):
        for key in self.required:
            if key not in data:
                raise ValidationError({key: f"Required for load: {key} ({data})/{self.required}"})
        return data


class SubSchema(BaseSchema):
    integer = fields.Integer()


class NestedSchema(BaseSchema):
    sub = fields.Nested(SubSchema, required=True)


class MixedMerged(BaseSchema):
    field = MultiNested([NestedSchema, Schema(["required27"])], merged=True)


def test_mixed_merged_concrete():
    schema = MixedMerged()
    schema.load({"field": {"sub": {"integer": 42}}})


def test_mixed_merged_blank_schema():
    schema = MixedMerged()
    schema.load({"field": {"required27": "27"}})


class MergedSchema(BaseSchema):
    cast_to_dict = True
    field = MultiNested([Schema(["required17"]), Schema(["required18"])], merged=True)


def test_load_and_dump_blank_schema():
    schema = Schema(["required42"], unknown=INCLUDE)
    assert schema.load({"required42": "42"}) == {"required42": "42"}
    assert schema.dump({"required84": "84"}) == {}


def test_load_merged_blank_schema():
    merged_blank = MergedSchema()
    data = {"field": {"required17": "17", "required18": "18"}}
    assert merged_blank.load(data) == data


def test_dump_merged_blank_schema():
    merged_blank = MergedSchema()
    data = {"field": {"required17": "17", "required18": "18"}}
    assert merged_blank.dump(data) == data


def test_error_works_on_load_with_blank_schema():
    merged_blank = MergedSchema()
    with pytest.raises(ValidationError):
        merged_blank.load({"field": {}})


def test_load_only_concreate_schemas():
    class SchemaA(BaseSchema):
        a = fields.Integer()

    class SchemaB(BaseSchema):
        b = fields.Integer()

    class SchemaC(BaseSchema):
        c = fields.Integer()

    schemas = [SchemaA, SchemaB, SchemaC]
    random.shuffle(schemas)

    class ConcreteSchema(BaseSchema):
        field = MultiNested(schemas, merged=True)

    concrete = ConcreteSchema()
    data = {"field": {"a": 1, "b": 2, "c": 3}}
    assert concrete.load(data) == data


def test_loading_data_invalid_in_all_schemas_fails():
    class SchemaA(BaseSchema):
        a = fields.Integer()

    class SchemaB(BaseSchema):
        @post_load
        def _post_load(self, data, many=False, partial=None):
            raise ValidationError("B")

    class MixedMultiNestedSchema(BaseSchema):
        field = MultiNested([SchemaA, SchemaB], merged=True)

    schema = MixedMultiNestedSchema()
    with pytest.raises(ValidationError):
        schema.load({"field": {"hallo": "welt"}})
