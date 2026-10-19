#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""How a filter takes its value from a clicked row, for a drill-down that carries it."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.gui.type_defs import ColumnName, FilterHTTPVariables
from cmk.gui.utils.labels import filter_http_vars_for_simple_label_group

type RowValues = Mapping[ColumnName, object]
type ObjectType = Literal["host", "service"]


@dataclass(frozen=True)
class LabelKey:
    object_type: ObjectType


@dataclass(frozen=True)
class TagGroupKey:
    """A tag group of the tag config, for service tags as well as host tags."""


@dataclass(frozen=True)
class AuxTagKey:
    """An aux tag of the tag config. The filter has one field per aux tag, so it takes at most
    `max_count`."""

    max_count: int


type FilterKey = LabelKey | TagGroupKey | AuxTagKey


@dataclass(frozen=True)
class Drilldown:
    """`variables` takes the row and the configured keys (label keys, tag groups or aux tags)
    and returns None when the row has no value. `key` says which kind of key the filter takes,
    if any."""

    columns: Sequence[ColumnName]
    variables: Callable[[RowValues, Sequence[str]], FilterHTTPVariables | None]
    key: FilterKey | None = None


def value(row: RowValues, column: ColumnName) -> str | None:
    cell = row.get(column)
    return None if cell is None or cell == "" else str(cell)


def text(variable: str, column: ColumnName) -> Drilldown:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        return None if (cell := value(row, column)) is None else {variable: cell}

    return Drilldown(columns=[column], variables=variables)


def checked_option(prefix: str, column: ColumnName) -> Drilldown:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        return None if (cell := value(row, column)) is None else {f"{prefix}{cell}": "on"}

    return Drilldown(columns=[column], variables=variables)


def single_item(variable: str, column: ColumnName) -> Drilldown:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        match row.get(column):
            case [str(item)]:
                return {variable: item}
            case _:
                return None

    return Drilldown(columns=[column], variables=variables)


def check_command(variable: str, column: ColumnName) -> Drilldown:
    # The filter matches the command with any arguments.
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        if (cell := value(row, column)) is None:
            return None
        return {variable: cell.split("!", 1)[0]}

    return Drilldown(columns=[column], variables=variables)


def mapping_value(row: RowValues, column: ColumnName, key: str) -> str | None:
    """The value under the key of a mapping column, such as a custom variable or a label."""
    mapping = row.get(column)
    if not isinstance(mapping, Mapping) or not (cell := mapping.get(key)):
        return None
    return str(cell)


def host_label_value(variable: str, label: str) -> Drilldown:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        cell = mapping_value(row, "host_labels", label)
        return None if cell is None else {variable: cell}

    return Drilldown(columns=["host_labels"], variables=variables)


def object_name(object_type: ObjectType) -> ColumnName:
    return "host_name" if object_type == "host" else "service_description"


def state(
    prefix: str, object_type: ObjectType, state_column: ColumnName | None = None
) -> Drilldown:
    name = object_name(object_type)
    column = state_column or f"{object_type}_state"
    has_been_checked = f"{object_type}_has_been_checked"

    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        # A missing object comes with empty defaults, which would read as pending.
        if value(row, name) is None or column not in row or has_been_checked not in row:
            return None
        if row[has_been_checked] != 1:
            return {f"{prefix}p": "on"}
        return {f"{prefix}{int(str(row[column]))}": "on"}

    return Drilldown(columns=[name, column, has_been_checked], variables=variables)


def state_type(object_type: ObjectType) -> Drilldown:
    name, column = object_name(object_type), f"{object_type}_state_type"

    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        if value(row, name) is None or (cell := value(row, column)) is None:
            return None
        return {f"is_{column}": cell}

    return Drilldown(columns=[name, column], variables=variables)


def labels(object_type: ObjectType) -> Drilldown:
    column = f"{object_type}_labels"

    def variables(row: RowValues, keys: Sequence[str]) -> FilterHTTPVariables | None:
        row_labels = row.get(column)
        if (
            not keys
            or not isinstance(row_labels, Mapping)
            or any(key not in row_labels for key in keys)
        ):
            return None
        return filter_http_vars_for_simple_label_group(
            [f"{key}:{row_labels[key]}" for key in keys], object_type
        )

    return Drilldown(columns=[column], variables=variables, key=LabelKey(object_type))


def tags(object_type: ObjectType) -> Drilldown:
    column = f"{object_type}_tags"

    def variables(row: RowValues, keys: Sequence[str]) -> FilterHTTPVariables | None:
        row_tags = row.get(column)
        if (
            not keys
            or not isinstance(row_tags, Mapping)
            or any(group not in row_tags for group in keys)
        ):
            return None
        http_vars: dict[str, str] = {}
        for index, group in enumerate(keys):
            http_vars[f"{object_type}_tag_{index}_grp"] = group
            http_vars[f"{object_type}_tag_{index}_op"] = "is"
            http_vars[f"{object_type}_tag_{index}_val"] = str(row_tags[group])
        return http_vars

    return Drilldown(columns=[column], variables=variables, key=TagGroupKey())
