#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.inventory import (
    load_delta_tree,
    load_tree,
)
from cmk.inventory.history import HistoryStore
from cmk.inventory.trees import ImmutableTree


@pytest.mark.usefixtures("request_context")
def test_load_tree_of_a_row_without_a_host_is_empty() -> None:
    assert load_tree(host_name=HostName(""), raw_status_data_tree=b"") == ImmutableTree()


@pytest.mark.usefixtures("request_context")
def test_load_delta_tree_no_such_timestamp(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        {"inv": "attr-1"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        {"inv-2": "attr"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        {"inv": "attr-3"},
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    with pytest.raises(MKGeneralException) as e:
        load_delta_tree(history_store, hostname, -1)
    assert str(e.value) == "Found no history entry at the time of '-1' for the host 'inv-host'"
