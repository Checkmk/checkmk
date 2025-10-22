#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.inventory_ui.v1_unstable import (
    BoolField,
    ChoiceField,
    Label,
    Node,
    NumberField,
    Table,
    TextField,
    Title,
    View,
)


def test_bool_field_empty_title() -> None:
    with pytest.raises(ValueError):
        BoolField(title=Title(""))


def test_number_field_empty_title() -> None:
    with pytest.raises(ValueError):
        NumberField(title=Title(""))


def test_text_field_empty_title() -> None:
    with pytest.raises(ValueError):
        TextField(title=Title(""))


def test_choice_field_empty_title() -> None:
    with pytest.raises(ValueError):
        ChoiceField(title=Title(""), mapping={"key": Label("Value")})


def test_choice_field_empty_mapping() -> None:
    with pytest.raises(ValueError):
        ChoiceField(Title("A title"), mapping={})


def test_view_empty_name() -> None:
    with pytest.raises(ValueError):
        View(name="", title=Title("A title"))


def test_view_empty_title() -> None:
    with pytest.raises(ValueError):
        View(name="view_name", title=Title(""))


def test_table_empty_column() -> None:
    with pytest.raises(ValueError):
        Table(columns={"": BoolField(Title("A title"))})


def test_node_empty_name() -> None:
    with pytest.raises(ValueError):
        Node(name="", title=Title("A title"), path=["path", "to", "node"])


def test_node_empty_title() -> None:
    with pytest.raises(ValueError):
        Node(name="path_to_node", title=Title(""), path=["path", "to", "node"])


def test_node_empty_path() -> None:
    with pytest.raises(ValueError):
        Node(name="path_to_node", title=Title("A title"), path=[])


def test_node_empty_edge() -> None:
    with pytest.raises(ValueError):
        Node(name="path_to_node", title=Title("A title"), path=["path", "", "node"])


def test_node_empty_attribute() -> None:
    with pytest.raises(ValueError):
        Node(
            name="path_to_node",
            title=Title("A title"),
            path=["path", "to", "node"],
            attributes={"": BoolField(Title("A title"))},
        )


def test_sort_key() -> None:
    def _sort_key_mac_address(mac_address: str) -> tuple[int, int, int, int, int, int]:
        first, second, third, fourth, fifth, sixth = mac_address.split(":")
        return (
            int(first, 16),
            int(second, 16),
            int(third, 16),
            int(fourth, 16),
            int(fifth, 16),
            int(sixth, 16),
        )

    field = TextField(Title("A title"), sort_key=_sort_key_mac_address)
    assert field.sort_key is not None
    assert field.sort_key("00:1A:2B:3C:4D:5E") == (0, 26, 43, 60, 77, 94)
