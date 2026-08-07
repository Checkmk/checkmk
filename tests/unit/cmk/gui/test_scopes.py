#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.scopes import (
    format_scopes,
    InvalidScopeError,
    normalize_scopes,
    parse_scopes,
    ScopeId,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("read", {ScopeId.READ}),
        # write implies read, so the pair is what a request to write means.
        ("write", {ScopeId.READ, ScopeId.WRITE}),
        ("read write", {ScopeId.READ, ScopeId.WRITE}),
    ],
)
def test_parse_scopes(raw: str, expected: set[ScopeId]) -> None:
    assert parse_scopes(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "unknown",
        # Strict, even if partially known.
        "read unknown",
        # Scope values are case-sensitive per RFC 6749 section 3.3.
        "READ",
    ],
)
def test_parse_scopes_rejects_unknown_values(raw: str) -> None:
    with pytest.raises(InvalidScopeError):
        parse_scopes(raw)


def test_parse_scopes_rejects_empty_scope_string() -> None:
    with pytest.raises(InvalidScopeError):
        parse_scopes("")


def test_normalize_scopes_write_implies_read() -> None:
    assert normalize_scopes({ScopeId.WRITE}) == {ScopeId.READ, ScopeId.WRITE}


@pytest.mark.parametrize(
    "scopes, expected",
    [
        ({ScopeId.READ}, "read"),
        ({ScopeId.READ, ScopeId.WRITE}, "read write"),
        # Ordering is stable.
        ({ScopeId.WRITE, ScopeId.READ}, "read write"),
        # Normalization is applied.
        ({ScopeId.WRITE}, "read write"),
    ],
)
def test_format_scopes(scopes: set[ScopeId], expected: str) -> None:
    assert format_scopes(scopes) == expected
