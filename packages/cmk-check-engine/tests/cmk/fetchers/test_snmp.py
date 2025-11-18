#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.fetchers.snmp import SNMPPluginStore, SNMPPluginStoreItem
from cmk.snmplib import SNMPDetectSpec, SNMPSectionName


def test_plugin_store_serialization_roundtrip() -> None:
    store = SNMPPluginStore(
        {
            SNMPSectionName("foo"): SNMPPluginStoreItem(
                trees=[], detect_spec=SNMPDetectSpec(), inventory=True
            )
        }
    )

    assert store == SNMPPluginStore.deserialize(store.serialize())
