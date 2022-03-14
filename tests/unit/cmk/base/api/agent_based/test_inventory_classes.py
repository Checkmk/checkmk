#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow


@pytest.mark.parametrize("class_", [TableRow, Attributes])
@pytest.mark.parametrize("path", [["a", 23], ("a", "b")])
def test_common_raise_path_type(class_, path):
    with pytest.raises(TypeError):
        _ = class_(path=path)


def test_common_kwarg_only():
    with pytest.raises(TypeError):
        _ = Attributes(["a"])  # type: ignore[misc] #pylint:disable= E1125, E1121
    with pytest.raises(TypeError):
        _ = TableRow(["a"], key_columns={"ding": "dong"})  # type: ignore[misc]   #pylint:disable= E1125, E1121


def test_atrributes_wrong_types():
    with pytest.raises(TypeError):
        _ = Attributes(
            path=["software", "os"],
            inventory_attributes={"version": (42, 23)},  # type: ignore[dict-item]
        )


def test_attributes_duplicate_keys():
    with pytest.raises(ValueError):
        _ = Attributes(
            path=["software", "os"],
            inventory_attributes={"version": "42"},
            status_attributes={"version": "42"},
        )


def test_attributes_instanciated():
    attr = Attributes(
        path=["software", "os"],
        status_attributes={"vendor": "emmentaler"},
        inventory_attributes={"version": "42"},
    )

    assert attr.path == ["software", "os"]
    assert attr.status_attributes == {"vendor": "emmentaler"}
    assert attr.inventory_attributes == {"version": "42"}
    assert (
        repr(attr)
        == "Attributes(path=['software', 'os'], inventory_attributes={'version': '42'}, status_attributes={'vendor': 'emmentaler'})"
    )

    attr2 = Attributes(
        path=["software", "os"],
        status_attributes={"vendor": "camembert"},
        inventory_attributes={"version": "42"},
    )
    assert attr == attr  # pylint: disable= comparison-with-itself
    assert attr2 != attr


def test_tablerow_missing_key_columns():
    with pytest.raises(TypeError):
        _ = TableRow(path=["hardware"], key_columns=None)  # type: ignore[arg-type]
        _ = TableRow(path=["hardware"], key_columns={})


def test_tablerow_wrong_types():
    with pytest.raises(TypeError):
        _ = TableRow(path=["hardware"], key_columns={23: 42})  # type: ignore[dict-item]


def test_tablerow_conflicting_keys():
    with pytest.raises(ValueError):
        _ = TableRow(
            path=["hardware"],
            key_columns={"foo": "bar"},
            status_columns={"foo": "bar"},
        )


def test_tablerow_instanciated():
    table_row = TableRow(
        path=["software", "os"],
        key_columns={"foo": "bar"},
        status_columns={"packages": 42},
        inventory_columns={"vendor": "emmentaler"},
    )

    assert table_row.path == ["software", "os"]
    assert table_row.key_columns == {"foo": "bar"}
    assert table_row.status_columns == {"packages": 42}
    assert table_row.inventory_columns == {"vendor": "emmentaler"}
    assert (
        repr(table_row)
        == "TableRow(path=['software', 'os'], key_columns={'foo': 'bar'}, inventory_columns={'vendor': 'emmentaler'}, status_columns={'packages': 42})"
    )

    table_row2 = TableRow(
        path=["software", "os"],
        key_columns={"foo": "bar"},
        status_columns={"packages": 42},
        inventory_columns={"vendor": "gorgonzola"},
    )
    assert table_row == table_row  # pylint: disable= comparison-with-itself
    assert table_row2 != table_row
