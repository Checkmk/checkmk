#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.inventory.host_labels import InventorizedHostLabelsStore


def test_inventorized_host_labels_store_load_default(tmp_path: Path) -> None:
    assert InventorizedHostLabelsStore(HostName("host"), tmp_path).load(debug=False) == {}


def test_inventorized_host_labels_store_save_load_roundtrip(tmp_path: Path) -> None:
    InventorizedHostLabelsStore(HostName("host"), tmp_path).save({"cmk/inventory/product": "foo"})
    assert InventorizedHostLabelsStore(HostName("host"), tmp_path).load(debug=False) == {
        "cmk/inventory/product": "foo"
    }
