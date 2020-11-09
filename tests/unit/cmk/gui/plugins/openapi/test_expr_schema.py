#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from marshmallow import Schema, fields, ValidationError

from cmk.gui.plugins.openapi.fields import ExprSchema


@pytest.fixture(name='schema')
def _schema():
    class QuerySchema(Schema):
        q = fields.Nested(ExprSchema())

    return QuerySchema()


def test_expr_schema(schema):
    from_json = schema.load({'q': '{"op": "=", "left": "host.name", "right": "example.com"}'})
    from_dict = schema.load({'q': {"op": "=", "left": "host.name", "right": "example.com"}})
    assert from_json == from_dict


def test_expr_schema_invalid_json(schema):
    with pytest.raises(ValidationError):
        schema.load({'q': '{"asdf'})
