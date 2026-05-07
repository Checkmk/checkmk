#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
from collections.abc import Generator, Sequence

from cmk.gui.openapi.framework.model.common_fields import BinaryBase64
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client.queries import ResultRow
from cmk.livestatus_client.types import Column

from .models.response_models import HostStatusObjectModel

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    )
)

_INVENTORY_COLUMN = "mk_inventory"


def host_object(host_name: str, host: ResultRow) -> HostStatusObjectModel:
    return HostStatusObjectModel(
        domainType="host",
        id=host_name,
        title=host_name,
        links=generate_links(
            domain_type="host", identifier=host_name, editable=False, deletable=False
        ),
        extensions={k: BinaryBase64(v) if isinstance(v, bytes) else v for k, v in host.items()},
    )


def contains_inventory_column(columns: Sequence[Column]) -> bool:
    return any(col.name == _INVENTORY_COLUMN for col in columns)


def fixup_inventory_row(row: ResultRow) -> ResultRow:
    if inventory_data := row.get(_INVENTORY_COLUMN):
        copy = dict(row)
        copy[_INVENTORY_COLUMN] = ast.literal_eval(inventory_data.decode("utf-8"))
        return ResultRow(copy)
    return row


def fixup_inventory_column(result: Generator[ResultRow]) -> Generator[ResultRow]:
    for row in result:
        yield fixup_inventory_row(row)
