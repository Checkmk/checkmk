#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence


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
