#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Final, Self

from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework.model import ApiOmitted

from ._api._filters import FILTER_NODE
from ._api._list_hosts import HostsRequestBody
from ._exceptions import InvalidHostListingError

_REQUEST_BODY: Final = TypeAdapter[HostsRequestBody](HostsRequestBody)


@dataclass(frozen=True)
class HostListing:
    sort: list[str]
    query: str
    filter: str | None
    limit: int | None

    @classmethod
    def from_request_body(cls, raw: str) -> Self:
        body = cls._validate(raw)
        return cls(
            sort=[] if isinstance(body.sort, ApiOmitted) else [str(sort) for sort in body.sort],
            query="" if isinstance(body.q, ApiOmitted) else body.q,
            filter=None
            if isinstance(body.filter, ApiOmitted)
            else FILTER_NODE.dump_json(body.filter).decode(),
            limit=body.limit,
        )

    @staticmethod
    def _validate(raw: str) -> HostsRequestBody:
        try:
            return _REQUEST_BODY.validate_json(raw)
        except ValidationError as exc:
            raise InvalidHostListingError(str(exc)) from exc
