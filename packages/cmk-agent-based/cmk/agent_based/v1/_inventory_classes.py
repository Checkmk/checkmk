#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plug-ins"""

import string
from collections.abc import Mapping
from typing import NamedTuple, NoReturn, Self

# make sure these two are consistent
_SDValue = int | float | str | bool | None
_ATTR_DICT_VAL_TYPES = (int, float, str, bool, type(None))

_VALID_CHARACTERS = set(string.ascii_letters + string.digits + "_-")


def _parse_valid_path(path: list[str]) -> list[str]:
    if not (path and isinstance(path, list) and all(isinstance(s, str) for s in path)):
        raise TypeError(f"'path' arg expected a non empty list[str], got {path!r}")
    invalid_chars = set("".join(path)) - _VALID_CHARACTERS
    if invalid_chars:
        raise ValueError(f"invalid characters in path: {''.join(invalid_chars)}")
    return path


def _raise_invalid_attr_dict(kwarg_name: str, dict_: Mapping[str, _SDValue]) -> NoReturn:
    value_types = ", ".join(t.__name__ for t in _ATTR_DICT_VAL_TYPES)
    raise TypeError(
        f"{kwarg_name} must be a dict with keys of type `str`"
        f" and values of type {value_types}. Got {dict_!r}"
    )


def _parse_valid_dict(
    kwarg_name: str, dict_: Mapping[str, _SDValue] | None
) -> Mapping[str, _SDValue]:
    if dict_ is None:
        return {}
    if not isinstance(dict_, dict):
        _raise_invalid_attr_dict(kwarg_name, dict_)
    if not all(
        isinstance(k, str) and isinstance(v, _ATTR_DICT_VAL_TYPES) for k, v in dict_.items()
    ):
        _raise_invalid_attr_dict(kwarg_name, dict_)
    return dict_


class _AttributesTuple(NamedTuple):
    path: list[str]
    inventory_attributes: Mapping[str, _SDValue]
    status_attributes: Mapping[str, _SDValue]


class Attributes(_AttributesTuple):
    """Attributes to be written at a node in the HW/SW Inventory"""

    def __new__(
        cls,
        *,
        path: list[str],
        inventory_attributes: Mapping[str, _SDValue] | None = None,
        status_attributes: Mapping[str, _SDValue] | None = None,
    ) -> Self:
        """

        Example:

            >>> _ = Attributes(
            ...     path = ["os", "vendor"],
            ...     inventory_attributes = {
            ...         "name" : "Micki$osft",
            ...         "date" : "1920",
            ...     },
            ...     status_attributes = {
            ...         "uptime" : 0,
            ...     },
            ... )

        """
        inventory_attributes = _parse_valid_dict("inventory_attributes", inventory_attributes)
        status_attributes = _parse_valid_dict("status_attributes", status_attributes)
        common_keys = set(inventory_attributes) & set(status_attributes)
        if common_keys:
            raise ValueError(
                f"keys must be either of type 'status' or 'inventory': {', '.join(common_keys)}"
            )

        return super().__new__(
            cls,
            path=_parse_valid_path(path),
            inventory_attributes=inventory_attributes,
            status_attributes=status_attributes,
        )


class _TableRowTuple(NamedTuple):
    path: list[str]
    key_columns: Mapping[str, _SDValue]
    inventory_columns: Mapping[str, _SDValue]
    status_columns: Mapping[str, _SDValue]


class TableRow(_TableRowTuple):
    """TableRow to be written into a Table at a node in the HW/SW Inventory"""

    def __new__(
        cls,
        *,
        path: list[str],
        key_columns: Mapping[str, _SDValue],
        inventory_columns: Mapping[str, _SDValue] | None = None,
        status_columns: Mapping[str, _SDValue] | None = None,
    ) -> Self:
        """

        Example:

            >>> _ = TableRow(
            ...     path = ["software", "applications", "oracle", "instance"],
            ...     key_columns = {
            ...         "sid" : "DECAF-FOOBAR",
            ...     },
            ...     inventory_columns = {
            ...         "version": "23.42",
            ...         "logmode": "debug",
            ...     },
            ...     status_columns = {
            ...         "db_uptime": 123456,
            ...     },
            ... )

        """
        if not (isinstance(key_columns, dict) and key_columns):
            raise TypeError(
                f"TableRows 'key_columns' expected non empty Dict[str, Any], got {key_columns!r}"
            )

        key_columns = _parse_valid_dict("key_columns", key_columns)
        inventory_columns = _parse_valid_dict("inventory_columns", inventory_columns)
        status_columns = _parse_valid_dict("status_columns", status_columns)

        for key in set(inventory_columns) | set(status_columns):
            if ((key in key_columns) + (key in inventory_columns) + (key in status_columns)) > 1:
                raise ValueError(f"conflicting key: {key!r}")

        return super().__new__(
            cls,
            path=_parse_valid_path(path),
            key_columns=key_columns,
            inventory_columns=inventory_columns,
            status_columns=status_columns,
        )
