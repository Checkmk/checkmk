#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The OAuth scope vocabulary and its wire format.

Deliberately free of Checkmk dependencies: this is the wire contract, shared by the OAuth
endpoints that hand scopes out and by cmk.gui.authorization, which resolves them to
permissions.
"""

import enum
from collections.abc import Iterable
from typing import Final


class ScopeId(enum.Enum):
    """The site API resource's scope vocabulary.

    Declaration order is the wire order, so one grant has one spelling.
    """

    READ = "read"
    WRITE = "write"


# Advertised in the RFC 8414 and RFC 9728 metadata documents.
SUPPORTED_SCOPES: Final[tuple[str, ...]] = tuple(scope.value for scope in ScopeId)

# We fall back to this if no scope is requested at all.
DEFAULT_SCOPE: Final[frozenset[ScopeId]] = frozenset({ScopeId.READ})


class InvalidScopeError(ValueError):
    """A scope string naming something outside SUPPORTED_SCOPES, or nothing."""


def normalize_scopes(scopes: Iterable[ScopeId]) -> frozenset[ScopeId]:
    """Apply the implications between scopes.

    Currently only: write implies read. More fine-grained scopes we may add later be reified here too.
    """
    normalized = set(scopes)
    if ScopeId.WRITE in normalized:
        normalized.add(ScopeId.READ)
    return frozenset(normalized)


def parse_scopes(raw: str) -> frozenset[ScopeId]:
    """Turn a space-separated scope string into the scopes it names.

    Raises InvalidScopeError for an unknown value or a string naming no scope.
    """
    requested = raw.split()
    if unknown := sorted(token for token in requested if token not in SUPPORTED_SCOPES):
        raise InvalidScopeError(" ".join(unknown))
    if not requested:
        raise InvalidScopeError("names no scope at all")
    return normalize_scopes(ScopeId(token) for token in requested)


def format_scopes(scopes: Iterable[ScopeId]) -> str:
    """Render scopes as the space-separated wire form of RFC 6749 section 3.3.

    Normalized first, so a grant has exactly one spelling.
    """
    granted = normalize_scopes(scopes)
    return " ".join(scope.value for scope in ScopeId if scope in granted)
