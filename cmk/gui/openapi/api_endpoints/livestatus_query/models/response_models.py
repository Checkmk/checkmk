#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Self

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import BinaryBase64, LivestatusValue
from cmk.livestatus_client.queries import ResultRow


@api_model
class LivestatusQueryResponse:
    """The result of a generic Livestatus query, as a flat self-describing wire shape.

    The resolved table name and column names are echoed back, and the result set is a list of
    row objects keyed by column name. Deliberately flat (no restful-objects collection envelope)
    because generic rows have no natural id, title, or links and the consumer is a machine.
    """

    table: str = api_field(
        description="The table that was queried.",
        example="hosts",
    )
    columns: list[str] = api_field(
        description="The columns present in each row, in order.",
        example=["name", "alias"],
    )
    rows: list[dict[str, LivestatusValue]] = api_field(
        description="The matching rows, each an object keyed by column name.",
        example=[{"name": "heute", "alias": "heute"}],
    )

    @classmethod
    def from_result(cls, table: str, columns: Sequence[str], rows: Iterable[ResultRow]) -> Self:
        """Build the response from a raw Livestatus result, encoding each cell for the wire.

        The single place cell encoding happens: a `bytes` cell becomes a `BinaryBase64` so it
        serializes to the `binary_base64` wire form; every other value passes through unchanged.
        There is deliberately NO `mk_inventory`-style special case -- a generic mechanism must
        not carry knowledge of one column of one table, so structured blobs stay base64-encoded
        rather than being parsed into nested objects.
        """
        return cls(
            table=table,
            columns=list(columns),
            rows=[
                {
                    key: BinaryBase64(value) if isinstance(value, bytes) else value
                    for key, value in row.items()
                }
                for row in rows
            ],
        )
