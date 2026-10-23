#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final, override

from cmk.gui.monitor.table_widget import InvalidSortError, TableCatalog

from ._api._validators import parse_host_sort_options
from ._models import HostOptionalField, HostSort, HostSortColumn, HostSortDirection


class HostTableCatalog(TableCatalog):
    def __init__(self, columns: Mapping[str, HostOptionalField | None]) -> None:
        self._columns = columns

    @property
    @override
    def column_ids(self) -> Sequence[str]:
        return list(self._columns)

    @override
    def validate(self, columns: Sequence[str], sort: Sequence[str]) -> None:
        if unknown := [column for column in columns if column not in self._columns]:
            raise ValueError(
                f"Unknown columns: {', '.join(unknown)}. Allowed columns: {', '.join(self._columns)}."
            )
        if len(set(columns)) != len(columns):
            raise ValueError("A column must not be repeated.")
        self.sorters(columns, sort)

    def fields(self, columns: Sequence[str]) -> frozenset[HostOptionalField]:
        return frozenset(
            field for column in columns if (field := self._columns.get(column)) is not None
        )

    @staticmethod
    def sorters(columns: Sequence[str], sort: Sequence[str]) -> list[HostSort]:
        try:
            sorters = parse_host_sort_options(list(sort))
        except ValueError as exc:
            raise InvalidSortError(str(exc)) from exc
        if hidden := [sorter.column.value for sorter in sorters if sorter.column not in columns]:
            raise InvalidSortError(
                f"Only a displayed column can sort the table, not: {', '.join(hidden)}."
            )
        return sorters or [HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC)]


HOST_TABLE: Final = HostTableCatalog(
    {
        "state": None,
        "modes": None,
        "name": None,
        "alias": HostOptionalField.ALIAS,
        "address": HostOptionalField.ADDRESS,
        "folder": HostOptionalField.FOLDER,
        "site_id": None,
        "last_check": HostOptionalField.LAST_CHECK,
        "last_state_change": HostOptionalField.LAST_STATE_CHANGE,
        "labels": HostOptionalField.LABELS,
        "tags": HostOptionalField.TAGS,
        "contacts": HostOptionalField.CONTACTS,
        "contact_groups": HostOptionalField.CONTACT_GROUPS,
        "num_services": HostOptionalField.NUM_SERVICES,
        "num_services_ok": HostOptionalField.NUM_SERVICES_OK,
        "num_services_warn": HostOptionalField.NUM_SERVICES_WARN,
        "num_services_crit": HostOptionalField.NUM_SERVICES_CRIT,
        "num_services_unknown": HostOptionalField.NUM_SERVICES_UNKNOWN,
        "num_services_pending": HostOptionalField.NUM_SERVICES_PENDING,
        "customer": None,
    }
)
