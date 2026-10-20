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

from ._api._validators import parse_service_sort_options
from ._models import ServiceOptionalField, ServiceSort


@dataclass(frozen=True)
class ServiceColumn:
    title: LazyString
    field: ServiceOptionalField | None = None


class ServiceTableCatalog(TableCatalog):
    def __init__(self, columns: Mapping[str, ServiceColumn]) -> None:
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

    def fields(self, columns: Sequence[str]) -> frozenset[ServiceOptionalField]:
        return frozenset(
            field
            for column in columns
            if (service_column := self._columns.get(column)) is not None
            and (field := service_column.field) is not None
        )

    @staticmethod
    def sorters(columns: Sequence[str], sort: Sequence[str]) -> list[ServiceSort]:
        try:
            sorters = parse_service_sort_options(list(sort))
        except ValueError as exc:
            raise InvalidSortError(str(exc)) from exc
        if hidden := [sorter.column.value for sorter in sorters if sorter.column not in columns]:
            raise InvalidSortError(
                f"Only a displayed column can sort the table, not: {', '.join(hidden)}."
            )
        return sorters


HOST_SERVICES_TABLE: Final = ServiceTableCatalog(
    {
        "state": ServiceColumn(_l("State")),
        "modes": ServiceColumn(_l("Mode")),
        "name": ServiceColumn(_l("Service")),
        "summary": ServiceColumn(_l("Summary")),
        "last_state_change": ServiceColumn(_l("Last state change")),
        "last_check": ServiceColumn(_l("Last check")),
        "labels": ServiceColumn(_l("Labels"), ServiceOptionalField.LABELS),
        "tags": ServiceColumn(_l("Tags"), ServiceOptionalField.TAGS),
        "contacts": ServiceColumn(_l("Contacts"), ServiceOptionalField.CONTACTS),
        "contact_groups": ServiceColumn(_l("Contact groups"), ServiceOptionalField.CONTACT_GROUPS),
        "groups": ServiceColumn(_l("Service groups"), ServiceOptionalField.GROUPS),
        "perfometer": ServiceColumn(_l("Perf-O-Meter")),
    }
)
