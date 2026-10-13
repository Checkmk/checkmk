#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Sequence

from .._models import ServiceSort, ServiceSortColumn, ServiceSortDirection


def validate_uniqueness[T](values: Sequence[T]) -> Sequence[T]:
    if len(values) != len(set(values)):
        raise ValueError("Duplicate values are not allowed.")
    return values


def validate_label_pairs(values: Sequence[str]) -> Sequence[str]:
    """A pair, or a prefix of one: 'key:value', 'key:val*' or 'ke*'."""
    for value in values:
        key, separator, label_value = value.partition(":")
        if not key:
            raise ValueError(f"Expected a 'key:value' pair, got {value!r}.")
        if not separator:
            if not key.endswith("*") or key == "*":
                raise ValueError(f"Expected a 'key:value' pair or a 'key*' prefix, got {value!r}.")
            continue
        if not label_value or label_value == "*":
            raise ValueError(f"Expected a value after the colon, got {value!r}.")
    return values


def validate_unix_timestamp(value: object) -> int:
    # A PlainValidator receives the raw body value, so this cannot be annotated `int`.
    # TypedPlainValidator would allow that, but raises TypeError -> 500 instead of 400 (CMK-38100).
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"Expected a unix timestamp in whole seconds, got {type(value).__name__!r}."
        )

    return value


def parse_service_search_query(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected a search string, got {type(value).__name__!r}.")

    return value.replace("\n", "").replace("\r", "").strip()


def parse_service_sort_options(value: object) -> list[ServiceSort]:
    if not isinstance(value, list):
        raise ValueError(f"Expected a list of sort values, got {type(value).__name__!r}.")

    sort_options = [_parse_service_sort_option(token) for token in value]

    sort_column_counts = Counter(option.column for option in sort_options)
    duplicate_columns = [name for name, count in sort_column_counts.items() if count > 1]

    if duplicate_columns:
        raise ValueError(f"The following columns were duplicated: {', '.join(duplicate_columns)}")

    return sort_options


def _parse_service_sort_option(token: object) -> ServiceSort:
    if not isinstance(token, str):
        raise ValueError(f"Expected a 'column:direction' string, got {type(token).__name__!r}.")

    column, separator, direction = token.partition(":")
    if not separator:
        raise ValueError(f"Expected a 'column:direction' value, got {token!r}.")
    try:
        sort_column = ServiceSortColumn(column)
    except ValueError:
        raise ValueError(
            f"Unknown sort column in {token!r}. Allowed columns: {ServiceSortColumn.options()}."
        ) from None
    try:
        sort_direction = ServiceSortDirection(direction)
    except ValueError:
        raise ValueError(
            f"Unknown sort direction in {token!r}. "
            f"Allowed directions: {ServiceSortDirection.options()}."
        ) from None
    return ServiceSort(column=sort_column, direction=sort_direction)
