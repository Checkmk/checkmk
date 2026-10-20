#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, override

from cmk.gui.i18n import _l
from cmk.gui.monitor.table_widget import InvalidSortError, TableCatalog
from cmk.web.utils.speaklater import LazyString

from ._api._validators import parse_host_sort_options
from ._models import HostOptionalField, HostSort, HostSortColumn, HostSortDirection


@dataclass(frozen=True)
class HostColumn:
    title: LazyString
    field: HostOptionalField | None = None


class HostTableCatalog(TableCatalog):
    def __init__(self, columns: Mapping[str, HostColumn]) -> None:
        self._columns = columns

    @property
    @override
    def column_ids(self) -> Sequence[str]:
        return list(self._columns)

    def title(self, column: str) -> str:
        return str(self._columns[column].title)

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
            field
            for column in columns
            if (host_column := self._columns.get(column)) is not None
            and (field := host_column.field) is not None
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


_ALL_HOSTS_COLUMNS: Final = {
    "state": HostColumn(_l("State")),
    "modes": HostColumn(_l("Mode")),
    "name": HostColumn(_l("Host")),
    "num_relations": HostColumn(_l("Relations"), HostOptionalField.NUM_RELATIONS),
    "alias": HostColumn(_l("Host alias"), HostOptionalField.ALIAS),
    "address": HostColumn(_l("IP address"), HostOptionalField.ADDRESS),
    "folder": HostColumn(_l("Folder"), HostOptionalField.FOLDER),
    "site_id": HostColumn(_l("Site")),
    "last_check": HostColumn(_l("Last check"), HostOptionalField.LAST_CHECK),
    "last_state_change": HostColumn(_l("Last state change"), HostOptionalField.LAST_STATE_CHANGE),
    "labels": HostColumn(_l("Labels"), HostOptionalField.LABELS),
    "tags": HostColumn(_l("Tags"), HostOptionalField.TAGS),
    "contacts": HostColumn(_l("Contacts"), HostOptionalField.CONTACTS),
    "contact_groups": HostColumn(_l("Contact groups"), HostOptionalField.CONTACT_GROUPS),
    "groups": HostColumn(_l("Host groups"), HostOptionalField.GROUPS),
    "num_services": HostColumn(_l("All services"), HostOptionalField.NUM_SERVICES),
    "num_services_ok": HostColumn(_l("OK"), HostOptionalField.NUM_SERVICES_OK),
    "num_services_warn": HostColumn(_l("Wa"), HostOptionalField.NUM_SERVICES_WARN),
    "num_services_crit": HostColumn(_l("Cr"), HostOptionalField.NUM_SERVICES_CRIT),
    "num_services_unknown": HostColumn(_l("Un"), HostOptionalField.NUM_SERVICES_UNKNOWN),
    "num_services_pending": HostColumn(_l("Pd"), HostOptionalField.NUM_SERVICES_PENDING),
    "customer": HostColumn(_l("Customer")),
}

ALL_HOSTS_TABLE: Final = HostTableCatalog(_ALL_HOSTS_COLUMNS)

HOST_TABLE: Final = HostTableCatalog(
    {
        column: spec
        for column, spec in _ALL_HOSTS_COLUMNS.items()
        if column not in {"num_relations", "groups"}
    }
)
