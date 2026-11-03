#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from cmk.gui.openapi.framework.model import ApiOmitted


class InvalidListingError(ValueError):
    pass


class _ListingRequestBody[N](Protocol):
    @property
    def limit(self) -> int | None: ...

    @property
    def sort(self) -> Sequence[object] | ApiOmitted: ...

    @property
    def q(self) -> str | ApiOmitted: ...

    @property
    def filter(self) -> N | ApiOmitted: ...


class _BodyAdapter[N](Protocol):
    def validate_json(self, data: str, /) -> _ListingRequestBody[N]: ...


class _FilterAdapter[N](Protocol):
    def dump_json(self, instance: N, /) -> bytes: ...


@dataclass(frozen=True)
class TableListing:
    sort: list[str]
    query: str
    filter: str | None
    limit: int | None


class ListingParser[N]:
    def __init__(self, body: _BodyAdapter[N], filter_node: _FilterAdapter[N]) -> None:
        self._body = body
        self._filter_node = filter_node

    def parse(self, raw: str) -> TableListing:
        body = self._validate(raw)
        return TableListing(
            sort=[] if isinstance(body.sort, ApiOmitted) else [str(sort) for sort in body.sort],
            query="" if isinstance(body.q, ApiOmitted) else body.q,
            filter=None
            if isinstance(body.filter, ApiOmitted)
            else self._filter_node.dump_json(body.filter).decode(),
            limit=body.limit,
        )

    def _validate(self, raw: str) -> _ListingRequestBody[N]:
        try:
            return self._body.validate_json(raw)
        except ValidationError as exc:
            raise InvalidListingError(str(exc)) from exc
