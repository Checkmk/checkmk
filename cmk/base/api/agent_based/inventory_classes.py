#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plugins
"""
import string
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Callable,
    Optional,
    Iterable,
    Union,
)
from cmk.utils.type_defs import (
    InventoryPluginName,
    ParsedSectionName,
    RuleSetName,
)

_VALID_CHARACTERS = set(string.ascii_letters + string.digits + "_-")


def _parse_valid_path(path: List[str]) -> List[str]:
    if not (path and isinstance(path, list) and all(isinstance(s, str) for s in path)):
        raise TypeError("'path' arg expected a non empty List[str], got %r" % path)
    invalid_chars = set("".join(path)) - _VALID_CHARACTERS
    if invalid_chars:
        raise ValueError("invalid characters in path: %r" % "".join(invalid_chars))
    return path


def _parse_valid_dict(dict_: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if dict_ is None:
        return {}
    if not (isinstance(dict_, dict) and all(isinstance(k, str) for k in dict_)):
        raise TypeError("Expected Dict[str, Any], got %r" % dict_)
    return dict_


def _parse_valid_values(dict_: Dict[str, str],) -> Dict[str, str]:
    if not all(isinstance(v, str) for v in dict_.values()):
        raise TypeError("Expected Dict[str, str], got %r" % dict_)
    return dict_


class Attributes(
        NamedTuple("_AttributesTuple", [
            ("path", List[str]),
            ("inventory_attributes", Dict[str, str]),
            ("status_attributes", Dict[str, str]),
        ])):
    """Attributes to be written at a node in the HW/SW inventory"""
    def __new__(
        cls,
        *,
        path: List[str],
        inventory_attributes: Optional[Dict[str, str]] = None,
        status_attributes: Optional[Dict[str, str]] = None,
    ) -> "Attributes":
        """

        Example:

            >>> Attributes(
            ...     path = ["os", "vendor"],
            ...     inventory_attributes = {
            ...         "name" : "Micki$osft",
            ...         "date" : "1920",
            ...     }
            ...     status_attributes = {
            ...         "uptime" : "0",
            ...     }
            ... )

        """
        inventory_attributes = _parse_valid_values(_parse_valid_dict(inventory_attributes))
        status_attributes = _parse_valid_values(_parse_valid_dict(status_attributes))
        common_keys = set(inventory_attributes) & set(status_attributes)
        if common_keys:
            raise ValueError("keys must be either of type 'status' or 'inventory': %s" %
                             ', '.join(common_keys))

        return super().__new__(cls,
                               path=_parse_valid_path(path),
                               inventory_attributes=inventory_attributes,
                               status_attributes=status_attributes)


class TableRow(
        NamedTuple("_TableRowTuple", [("path", List[str]), ("key_columns", Dict[str, Any]),
                                      ("inventory_columns", Dict[str, Any]),
                                      ("status_columns", Dict[str, Any])]),):
    """TableRow to be written into a Table at a node in the HW/SW inventory"""
    def __new__(
        cls,
        *,
        path: List[str],
        key_columns: Dict[str, Any],
        inventory_columns: Optional[Dict[str, Any]] = None,
        status_columns: Optional[Dict[str, Any]] = None,
    ) -> "TableRow":
        """

        Example:

            >>> TableRow(
            ...     path = ["software", "applications", "oracle", "instance"],
            ...     key_columns = {
            ...         "sid" : item_data['sid'],
            ...     },
            ...     inventory_columns = {
            ...         "version": item_data['version'],
            ...         "openmode": item_data['openmode'],
            ...         "logmode": item_data['log_mode'],
            ...         "logins": item_data['logins'],
            ...         "db_creation_time": _parse_raw_db_creation_time(item_data['db_creation_time']),
            ...     }
            ...     status_columns = {
            ...         "db_uptime": up_seconds,
            ...     }
            ... )

        """
        if not (isinstance(key_columns, dict) and key_columns):
            raise TypeError("TableRows 'key_columns' expected non empty Dict[str, Any], got %r" %
                            (key_columns,))

        key_columns = _parse_valid_dict(key_columns)
        inventory_columns = _parse_valid_dict(inventory_columns)
        status_columns = _parse_valid_dict(status_columns)

        for key in set(inventory_columns) | set(status_columns):
            if ((key in key_columns) + (key in inventory_columns) + (key in status_columns)) > 1:
                raise ValueError("conflicting key: %s" % key)

        return super().__new__(
            cls,
            path=_parse_valid_path(path),
            key_columns=key_columns,
            inventory_columns=inventory_columns,
            status_columns=status_columns,
        )


InventoryResult = Iterable[Union[Attributes, TableRow]]
InventoryFunction = Callable[..., InventoryResult]
InventoryPlugin = NamedTuple(
    "InventoryPlugin",
    [
        ("name", InventoryPluginName),
        ("sections", List[ParsedSectionName]),
        ("inventory_function", InventoryFunction),
        ("inventory_default_parameters", Dict[str, Any]),
        ("inventory_ruleset_name", Optional[RuleSetName]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)
