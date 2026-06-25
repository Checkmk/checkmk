#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from marshmallow import missing, Schema, ValidationError

from cmk.fields import String
from cmk.fields.base import List, Nested


def test_nested_unique_items_detects_duplicates() -> None:
    class Service(Schema):
        host = String(required=True)
        description = String(required=True)
        recur = String()

    class Bulk(Schema):
        entries = Nested(
            Service,
            many=True,
            uniqueItems=True,
            required=False,
            load_default=list,
        )

    entries = [
        {"host": "example", "description": "CPU load", "recur": "week"},
        {"host": "example", "description": "CPU load", "recur": "day"},
        {"host": "host", "description": "CPU load"},
    ]
    with pytest.raises(ValidationError, match="Duplicate entry found at entry #2"):
        Bulk().load({"entries": entries})


def test_nested_load_default() -> None:
    class Service(Schema):
        host = String(required=True)

    class Bulk(Schema):
        entries = Nested(
            Service,
            many=True,
            uniqueItems=True,
            required=False,
            load_default=list,
        )

    schema = Bulk()
    assert schema.fields["entries"].load_default is not missing
    assert schema.load({}) == {"entries": []}


def test_list_unique_items_scalar_duplicates() -> None:
    class Foo(Schema):
        id = String()
        lists = List(String(), uniqueItems=True)

    with pytest.raises(ValidationError, match="Duplicate entry found at entry #2"):
        Foo().load({"lists": ["2", "2"]})


def test_list_unique_items_nested_duplicates() -> None:
    class Foo(Schema):
        id = String()
        lists = List(String(), uniqueItems=True)

    class Bar(Schema):
        entries = List(Nested(Foo), allow_none=False, required=True, uniqueItems=True)

    with pytest.raises(ValidationError, match="Duplicate entry found at entry #3"):
        Bar().load({"entries": [{"id": "1"}, {"id": "2"}, {"id": "2"}]})


def test_list_unique_items_nested_list_duplicates() -> None:
    class Foo(Schema):
        id = String()
        lists = List(String(), uniqueItems=True)

    class Bar(Schema):
        entries = List(Nested(Foo), allow_none=False, required=True, uniqueItems=True)

    with pytest.raises(ValidationError, match="Duplicate entry found at entry #2"):
        Bar().load({"entries": [{"lists": ["2"]}, {"lists": ["2"]}]})
