#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plugins
"""
import abc
import string
from typing import Any, Dict, List, Optional, Type

from cmk.base.api.agent_based.type_defs import ABCInventoryGenerated


class ABCPathedObject(abc.ABC, ABCInventoryGenerated):

    VALID_CHARACTERS = set(string.ascii_letters + string.digits + "_-")

    @classmethod
    def validate_path(cls, path: List[str]) -> None:
        if not (path and isinstance(path, list) and all(isinstance(s, str) for s in path)):
            raise TypeError("%s 'path' arg expected a non empty List[str], got %r" %
                            (cls.__name__, path))
        invalid_chars = set("".join(path)) - cls.VALID_CHARACTERS
        if invalid_chars:
            raise ValueError("invalid characters in path: %r" % "".join(invalid_chars))

    def __init__(self, path: List[str]) -> None:
        self.validate_path(path)
        self._path = path

    @property
    def path(self) -> List[str]:
        return self._path

    @staticmethod
    def _validate_dict(
        name: str,
        dict_: Dict[str, Any],
        value_class: Optional[Type] = None,
    ) -> None:
        if not (isinstance(dict_, dict) and all(isinstance(k, str) for k in dict_) and
                (value_class is None or all(isinstance(v, value_class) for v in dict_.values()))):
            raise TypeError("Attributes %r expected Dict[str, %s], got %r" % (
                name,
                'Any' if value_class is None else value_class.__name__,
                dict_,
            ))


class Attributes(ABCPathedObject):
    """Attributes to be written at a node in the HW/SW inventory"""
    def __init__(
        self,
        *,
        path: List[str],
        inventory_attributes: Optional[Dict[str, str]] = None,
        status_attributes: Optional[Dict[str, str]] = None,
    ) -> None:
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
        super(Attributes, self).__init__(path)

        if inventory_attributes is None:
            inventory_attributes = {}
        if status_attributes is None:
            status_attributes = {}

        self._validate_dict("inventory_attributes", inventory_attributes, str)
        self._validate_dict("status_attributes", status_attributes, str)

        common_keys = set(inventory_attributes) & set(status_attributes)
        if common_keys:
            raise ValueError("keys must be either of type 'status' or 'inventory': %s" %
                             ', '.join(common_keys))

        self._inventory_attributes = inventory_attributes
        self._status_attributes = status_attributes

    @property
    def inventory_attributes(self):
        return self._inventory_attributes

    @property
    def status_attributes(self):
        return self._status_attributes


class TableRow(ABCPathedObject, ABCInventoryGenerated):
    """TableRow to be written into a Table at a node in the HW/SW inventory"""
    def __init__(
        self,
        *,
        path: List[str],
        key_columns: Dict[str, Any],
        inventory_columns: Optional[Dict[str, Any]] = None,
        status_columns: Optional[Dict[str, Any]] = None,
    ) -> None:
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
        super(TableRow, self).__init__(path)

        if not isinstance(key_columns, dict):
            raise TypeError("TableRows 'key_columns' expected non empty Dict[str, Any], got %r" %
                            (key_columns,))
        if not key_columns:
            raise ValueError("TableRows 'key_columns' expected non empty Dict[str, Any], got %r" %
                             (key_columns,))

        if inventory_columns is None:
            inventory_columns = {}
        if status_columns is None:
            status_columns = {}

        self._validate_dict("key_columns", key_columns)
        self._validate_dict("inventory_columns", inventory_columns)
        self._validate_dict("status_columns", status_columns)

        for key in set(inventory_columns) | set(status_columns):
            if ((key in key_columns) + (key in inventory_columns) + (key in status_columns)) > 1:
                raise ValueError("conflicting key: %s" % key)

        self._key_columns = key_columns
        self._inventory_columns = inventory_columns
        self._status_columns = status_columns

    @property
    def key_columns(self) -> Dict[str, Any]:
        return self._key_columns

    @property
    def inventory_columns(self) -> Dict[str, Any]:
        return self._inventory_columns

    @property
    def status_columns(self) -> Dict[str, Any]:
        return self._status_columns
