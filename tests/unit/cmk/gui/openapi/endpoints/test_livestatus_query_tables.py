#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.openapi.api_endpoints.livestatus_query._tables import (
    INTENTIONALLY_NOT_EXPOSED,
    LIVESTATUS_TABLES,
    resolve_table,
)
from cmk.livestatus_client import tables
from cmk.livestatus_client.types import Table


def _exported_table_classes() -> dict[str, type[Table]]:
    """The Table subclasses the package currently exports, keyed by wire name."""
    exported: dict[str, type[Table]] = {}
    for name in tables.__all__:
        obj = getattr(tables, name)
        if isinstance(obj, type) and issubclass(obj, Table):
            exported[obj.__tablename__] = obj
    return exported


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("__class__", id="dunder-class"),
        pytest.param("__init__", id="dunder-init"),
        pytest.param("Hosts", id="class-name-not-wire-name"),
        pytest.param("statehist", id="unexported-package-module"),
        pytest.param("hosts\nColumnHeaders: on", id="lql-injection-newline"),
        pytest.param("", id="empty"),
    ],
)
def test_table_registry_rejects_non_table_identifiers(name: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        resolve_table(name)
    message = str(exc_info.value)
    # "downtimes" is a supported name that appears in no rejected input above, so
    # its presence proves the supported-names list is in the message rather than
    # merely the echoed (and here injection-shaped) input.
    assert "Supported tables are:" in message and "downtimes" in message, (
        f"resolve_table({name!r}) must reject with an error listing the supported "
        f"table names, got: {message!r}"
    )


def test_registry_and_intentionally_not_exposed_partition_exported_tables() -> None:
    exported = _exported_table_classes()
    exported_names = {cls.__name__ for cls in exported.values()}
    registry_names = {cls.__name__ for cls in LIVESTATUS_TABLES.values()}

    assert set(LIVESTATUS_TABLES.values()) <= set(exported.values()), (
        "Every registry entry must be a genuinely exported Table class: "
        f"registry-only={sorted(registry_names - exported_names)}"
    )
    assert registry_names | INTENTIONALLY_NOT_EXPOSED == exported_names, (
        "Every exported Table class must be consciously accounted for -- either "
        "REST-exposed in LIVESTATUS_TABLES or opted out via "
        "INTENTIONALLY_NOT_EXPOSED (a drift changes what any authenticated HTTP "
        "client may read): "
        f"unaccounted={sorted(exported_names - registry_names - INTENTIONALLY_NOT_EXPOSED)}, "
        f"stale={sorted((registry_names | INTENTIONALLY_NOT_EXPOSED) - exported_names)}"
    )
    assert not registry_names & INTENTIONALLY_NOT_EXPOSED, (
        "A table cannot be both REST-exposed and intentionally not exposed: "
        f"overlap={sorted(registry_names & INTENTIONALLY_NOT_EXPOSED)}"
    )
