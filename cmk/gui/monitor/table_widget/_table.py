#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import override, Protocol

from cmk.gui.type_defs import FilterName
from cmk.web.utils.speaklater import LazyString


class InvalidSortError(ValueError):
    pass


class _SortColumn(Protocol):
    @property
    def value(self) -> str: ...


class _Sorter(Protocol):
    @property
    def column(self) -> _SortColumn: ...


class TableCatalog[F](ABC):
    @property
    @abstractmethod
    def column_ids(self) -> Sequence[str]: ...

    @abstractmethod
    def title(self, column: str) -> str: ...

    @abstractmethod
    def validate(self, columns: Sequence[str], sort: Sequence[str]) -> None: ...

    @abstractmethod
    def fields(self, columns: Sequence[str]) -> frozenset[F]: ...


@dataclass(frozen=True)
class TableColumn[F]:
    title: LazyString
    field: F | None = None


class ColumnCatalog[F, S: _Sorter](TableCatalog[F]):
    def __init__(
        self,
        columns: Mapping[str, TableColumn[F]],
        parse_sort: Callable[[list[str]], list[S]],
        default_sort: Sequence[S] = (),
    ) -> None:
        self._columns = columns
        self._parse_sort = parse_sort
        self._default_sort = default_sort

    @property
    @override
    def column_ids(self) -> Sequence[str]:
        return list(self._columns)

    @override
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

    @override
    def fields(self, columns: Sequence[str]) -> frozenset[F]:
        return frozenset(
            field
            for column in columns
            if (table_column := self._columns.get(column)) is not None
            and (field := table_column.field) is not None
        )

    def sorters(self, columns: Sequence[str], sort: Sequence[str]) -> list[S]:
        try:
            sorters = self._parse_sort(list(sort))
        except ValueError as exc:
            raise InvalidSortError(str(exc)) from exc
        if hidden := [
            sorter.column.value for sorter in sorters if sorter.column.value not in columns
        ]:
            raise InvalidSortError(
                f"Only a displayed column can sort the table, not: {', '.join(hidden)}."
            )
        return sorters or list(self._default_sort)


@dataclass(frozen=True)
class TableRows[R]:
    rows: Sequence[R]
    matched: int
    total: int
    unapplied_filters: Sequence[FilterName]
    unreachable_sites: Sequence[str]
