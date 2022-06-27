#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from marshmallow import Schema, ValidationError

from cmk.utils.livestatus_helpers.tables import Hosts

from cmk.gui import fields


@pytest.fixture(name="schema", scope="module")
def _schema():
    class QuerySchema(Schema):
        q = fields.query_field(Hosts, required=True)

    return QuerySchema()


def test_expr_schema(schema) -> None:
    from_json = schema.load({"q": '{"op": "=", "left": "hosts.name", "right": "example.com"}'})
    from_dict = schema.load({"q": {"op": "=", "left": "hosts.name", "right": "example.com"}})
    assert not isinstance(from_json["q"], dict)
    assert not isinstance(from_dict["q"], dict)


def test_expr_schema_without_table_name(schema) -> None:
    schema.load({"q": {"op": "=", "left": "name", "right": "example.com"}})


def test_expr_schema_with_wrong_column(schema) -> None:
    with pytest.raises(ValidationError):
        schema.load({"q": {"op": "=", "left": "foo", "right": "example.com"}})

    with pytest.raises(ValidationError):
        schema.load({"q": {"op": "=", "left": "hosts.foo", "right": "example.com"}})


def test_expr_schema_sticks_to_table(schema) -> None:
    with pytest.raises(ValidationError):
        schema.load({"q": {"op": "=", "left": "services.name", "right": "example.com"}})


def test_expr_schema_invalid_json(schema) -> None:
    with pytest.raises(ValidationError):
        schema.load({"q": '{"asdf'})
