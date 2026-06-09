#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.dcd_connectors.internal import (
    Connector,
    ConnectorContext,
    ConnectorSpec,
    entry_point_prefixes,
    NullObject,
)


def _dummy_factory(_ctx: ConnectorContext) -> Connector[str]:
    raise NotImplementedError


def test_connector_spec_stores_all_fields() -> None:
    spec = ConnectorSpec[str](
        name="test",
        create_connector=_dummy_factory,
        connector_object_class=NullObject,
    )
    assert spec.name == "test"
    assert spec.create_connector is _dummy_factory
    assert spec.connector_object_class is NullObject


def test_connector_spec_name_used_by_discovery() -> None:
    spec = ConnectorSpec[str](
        name="my_connector",
        create_connector=_dummy_factory,
        connector_object_class=NullObject,
    )
    assert spec.name == "my_connector"


def test_entry_point_prefixes_contains_connector_spec() -> None:
    prefixes = entry_point_prefixes()
    assert ConnectorSpec in prefixes


def test_entry_point_prefix_for_connector_spec() -> None:
    prefixes = entry_point_prefixes()
    assert prefixes[ConnectorSpec] == "connector_"
